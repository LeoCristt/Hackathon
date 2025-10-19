import torch
import numpy as np
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, PreTrainedTokenizerBase
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Any, Optional
import logging
from peft import PeftModel
from sentence_transformers import SentenceTransformer
from razdel import sentenize
from numpy.typing import NDArray
import os
import pika
import json
import chromadb
from chromadb import HttpClient
from chromadb.config import Settings
import uuid
import time
from pythonjsonlogger import jsonlogger
from metrics import (
    ai_requests_total, ai_request_duration_seconds, ai_tokens_used,
    ai_agent_selection_similarity, ai_context_similarity, ai_special_cases_total,
    ai_active_chats, ai_history_truncation_total, start_metrics_server
)

# Настройка структурированного JSON логирования
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s',
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    json_ensure_ascii=False
)
logHandler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Используемое устройство: {device}")

base_dir = os.path.dirname(os.path.abspath(__file__))

# --- Инициализация ChromaDB ---
chroma_host = os.getenv("CHROMADB_HOST", "localhost")
chroma_port = int(os.getenv("CHROMADB_PORT", 8000))
chroma_client = HttpClient(
    host=chroma_host,
    port=chroma_port,
    settings=Settings(allow_reset=True, anonymized_telemetry=False)
)

collection_name = "paragraph_embeddings"
try:
    collection = chroma_client.get_collection(collection_name)
    logger.info(f"Коллекция {collection_name} найдена в ChromaDB.")
except Exception as e:
    logger.info(f"Создаём новую коллекцию {collection_name} в ChromaDB: {e}")
    collection = chroma_client.create_collection(collection_name)

# --- Разделение на абзацы ---
def split_into_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n', text) if p.strip()]
    return paragraphs

# Загрузка базовой модели
model = AutoModelForCausalLM.from_pretrained(os.path.join(base_dir, "quantized_model"))
base_tokenizer = AutoTokenizer.from_pretrained(os.path.join(base_dir, "quantized_model"))
if base_tokenizer.pad_token is None:
    base_tokenizer.pad_token = base_tokenizer.eos_token

# --- Словарь для выбора модели, токенизатора и пути к файлу ---
agent_map = {
    "Сеть": {
        "model": None,
        "tokenizer": None,
        "file_path": os.path.join(base_dir, "Сеть.txt")
    },
    "Приложение": {
        "model": None,
        "tokenizer": None,
        "file_path": os.path.join(base_dir, "Приложение.txt")
    },
    "Оборудование": {
        "model": None,
        "tokenizer": None,
        "file_path": os.path.join(base_dir, "Оборудование.txt")
    },
    "Доступ и пароли": {
        "model": None,
        "tokenizer": None,
        "file_path": os.path.join(base_dir, "Доступ и пароли.txt")
    },
    "Безопасность": {
        "model": None,
        "tokenizer": None,
        "file_path": os.path.join(base_dir, "Безопасность.txt")
    }
}

# --- Загрузка моделей и токенизаторов ---
for agent in agent_map:
    agent_map[agent]["tokenizer"] = AutoTokenizer.from_pretrained(os.path.join(base_dir, f"{agent}/best_model"))
    agent_map[agent]["model"] = PeftModel.from_pretrained(model, os.path.join(base_dir, f"{agent}/best_model"))
    if agent_map[agent]["tokenizer"].pad_token is None:
        agent_map[agent]["tokenizer"].pad_token = agent_map[agent]["tokenizer"].eos_token

local_emb_model_path = os.path.join(base_dir, "frida_embedding_model")
emb_model = SentenceTransformer(local_emb_model_path, device=device)

class ParagraphRetriever(BaseRetriever):
    paragraphs: Dict[str, List[str]]  # Храним параграфы по агентам
    paragraph_embeddings: Dict[str, List[NDArray]]  # Храним эмбеддинги по агентам
    embeddings_model: SentenceTransformer
    similarity_threshold: float = 0.25
    prompt_token_len: int = 0
    history_tokens: int = 0
    question_tokens: int = 0
    reserved_output_tokens: int = 150
    tokenizer: Optional[PreTrainedTokenizerBase] = None
    current_agent: Optional[str] = None  # ← добавьте эту строку

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_context_tokens = 0
        template_sample = "Ты — помощник, который строго отвечает только на основании предоставленного контекста и истории чата в одно предложение. Если контекста нет, отвечай на общие вопросы как дружелюбный бот (приветствия, прощания и т.д.).\n\n"
        self.tokenizer = agent_map["Сеть"]["tokenizer"]
        self.prompt_token_len = len(self.tokenizer.encode(template_sample))
        self.paragraphs = {}  # Кэш параграфов
        self.paragraph_embeddings = {}  # Кэш эмбеддингов
        self.load_all_paragraphs()  # Загружаем все эмбеддинги при инициализации

    def set_dynamic_limits(self, question_tokens: int, history_tokens: int, max_total_tokens: int = 8192):
        self.question_tokens = question_tokens
        self.history_tokens = history_tokens

    def load_all_paragraphs(self):
        """Загружает или вычисляет эмбеддинги параграфов для всех агентов и кэширует их."""
        for agent, config in agent_map.items():
            file_path = config["file_path"]
            if not os.path.exists(file_path):
                logger.error(f"Файл {file_path} не найден.")
                self.paragraphs[agent] = []
                self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                continue
            
            # Чтение файла
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            paragraphs = split_into_paragraphs(text)
            logger.info(f"Разбито на {len(paragraphs)} абзацев из файла {file_path}")

            try:
                # Проверка, есть ли записи в ChromaDB
                results = collection.get(where={"agent": agent}, include=["documents", "embeddings", "metadatas"])
                existing_ids = results["ids"]
                logger.info(f"Найдено {len(existing_ids)} записей в ChromaDB для агента {agent}")

                if not existing_ids:
                    if not paragraphs:
                        logger.warning(f"Нет параграфов для агента {agent}")
                        self.paragraphs[agent] = []
                        self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                        continue
                    
                    # Вычисление эмбеддингов
                    paragraph_embeddings = self.embeddings_model.encode(
                        paragraphs,
                        prompt_name="search_document",
                        convert_to_numpy=True,
                        normalize_embeddings=True
                    )
                    
                    # Проверка формы и типа эмбеддингов
                    if not isinstance(paragraph_embeddings, np.ndarray) or paragraph_embeddings.ndim != 2:
                        logger.error(f"Некорректная форма эмбеддингов для агента {agent}: {type(paragraph_embeddings)}")
                        self.paragraphs[agent] = []
                        self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                        continue
                    
                    # Проверка на NaN
                    if np.any(np.isnan(paragraph_embeddings)):
                        logger.error(f"Обнаружены NaN в эмбеддингах для агента {agent}")
                        self.paragraphs[agent] = []
                        self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                        continue
                    
                    # Сохранение в ChromaDB
                    ids = [f"{agent}_{i}" for i in range(len(paragraphs))]
                    collection.add(
                        documents=paragraphs,
                        embeddings=paragraph_embeddings.tolist(),
                        metadatas=[{"agent": agent} for _ in paragraphs],
                        ids=ids
                    )
                    logger.info(f"Сохранены {len(paragraphs)} эмбеддингов для агента {agent} в ChromaDB, shape: {paragraph_embeddings.shape}")
                    self.paragraphs[agent] = paragraphs
                    self.paragraph_embeddings[agent] = paragraph_embeddings
                else:
                    # Загрузка из ChromaDB
                    paragraphs = results["documents"]
                    embeddings = results["embeddings"]
                    
                    if not paragraphs or not embeddings:
                        logger.error(f"Пустые данные из ChromaDB для агента {agent}: documents={len(paragraphs)}, embeddings={len(embeddings)}")
                        self.paragraphs[agent] = []
                        self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                        continue
                    
                    # Преобразование эмбеддингов
                    try:
                        embeddings = np.array(embeddings, dtype=np.float32)
                        if embeddings.ndim != 2 or embeddings.shape[0] != len(paragraphs):
                            logger.error(f"Некорректная форма эмбеддингов для агента {agent}: shape={embeddings.shape}, expected {len(paragraphs)} rows")
                            self.paragraphs[agent] = []
                            self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                            continue
                        
                        if np.any(np.isnan(embeddings)):
                            logger.error(f"Обнаружены NaN в эмбеддингах из ChromaDB для агента {agent}")
                            self.paragraphs[agent] = []
                            self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                            continue
                        
                        self.paragraphs[agent] = paragraphs
                        self.paragraph_embeddings[agent] = embeddings
                        logger.info(f"Загружено {len(paragraphs)} абзацев для агента {agent}, embeddings shape: {embeddings.shape}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка преобразования эмбеддингов из ChromaDB для агента {agent}: {e}")
                        self.paragraphs[agent] = []
                        self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)
                        
            except Exception as e:
                logger.error(f"Ошибка при загрузке/сохранении эмбеддингов для агента {agent}: {e}")
                self.paragraphs[agent] = []
                self.paragraph_embeddings[agent] = np.array([], dtype=np.float32)

    def select_agent(self, query: str) -> Tuple[PreTrainedTokenizerBase, Any, str]:
        query_emb = self.embeddings_model.encode(
            query,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        agent_names = list(agent_map.keys())
        agent_embs = self.embeddings_model.encode(
            agent_names,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        sims = cosine_similarity([query_emb], agent_embs)[0]
        max_sim = max(sims)
        max_idx = sims.argmax()

        if max_sim < self.similarity_threshold:
            return None, None, None
        selected_agent = agent_names[max_idx]

        # Записываем метрику схожести с агентом
        ai_agent_selection_similarity.labels(agent=selected_agent).observe(float(max_sim))

        logger.info(f"Выбран агент: {selected_agent} (similarity: {max_sim:.2f})")
        return agent_map[selected_agent]["tokenizer"], agent_map[selected_agent]["model"], agent_map[selected_agent]["file_path"]

    def load_paragraphs(self, file_path: str) -> Tuple[List[str], List[NDArray]]:
        agent = os.path.basename(file_path).split(".")[0]
        if agent not in self.paragraphs or agent not in self.paragraph_embeddings:
            logger.error(f"Эмбеддинги для агента {agent} не найдены в кэше.")
            return [], []
        logger.info(f"Используется кэш: загружено {len(self.paragraphs[agent])} абзацев для агента {agent}")
        return self.paragraphs[agent], self.paragraph_embeddings[agent]

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        Получает релевантные документы на основе запроса, используя косинусное сходство.
        
        Args:
            query (str): Входной запрос пользователя.
            
        Returns:
            List[Document]: Список релевантных документов или сообщение об ошибке.
        """
        if not query or not isinstance(query, str):
            logger.error("Запрос пуст или не является строкой")
            return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]

        if not self.current_agent or self.current_agent not in self.paragraph_embeddings:
            logger.error(f"Текущий агент {self.current_agent} не найден или отсутствуют эмбеддинги")
            return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]

        try:
            # Кодирование запроса
            query_emb = self.embeddings_model.encode(
                query,
                prompt_name="search_query",
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            if np.any(np.isnan(query_emb)):
                logger.error("Обнаружены NaN в эмбеддингах запроса")
                return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]

            query_emb = query_emb.reshape(1, -1) if query_emb.ndim == 1 else query_emb
            logger.info(f"Query embedding shape: {query_emb.shape}")

            # Получение эмбеддингов параграфов
            paragraph_embs = self.paragraph_embeddings[self.current_agent]
            if not isinstance(paragraph_embs, np.ndarray) or paragraph_embs.ndim != 2 or paragraph_embs.size == 0:
                logger.error(f"Эмбеддинги для агента {self.current_agent} некорректны, type: {type(paragraph_embs)}, shape: {getattr(paragraph_embs, 'shape', 'None')}")
                # Попробуем загрузить из ChromaDB напрямую
                results = collection.query(
                    query_embeddings=[query_emb[0].tolist()],
                    where={"agent": self.current_agent},
                    n_results=10,
                    include=["documents", "metadatas", "embeddings"]
                )
                if not results["documents"] or not results["embeddings"]:
                    logger.error(f"Пустые данные из ChromaDB для агента {self.current_agent}: documents={len(results['documents'])}, embeddings={len(results['embeddings'])}")
                    return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]
                
                self.paragraphs[self.current_agent] = results["documents"]
                self.paragraph_embeddings[self.current_agent] = np.array(results["embeddings"], dtype=np.float32)
                paragraph_embs = self.paragraph_embeddings[self.current_agent]
                logger.info(f"Загружено {len(results['documents'])} документов из ChromaDB для агента {self.current_agent}")

            if np.any(np.isnan(paragraph_embs)):
                logger.error(f"Обнаружены NaN в эмбеддингах параграфов для агента {self.current_agent}")
                return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]

            logger.info(f"Paragraph embeddings shape: {paragraph_embs.shape}")

            # Вычисление косинусного сходства
            sims = cosine_similarity(query_emb, paragraph_embs)[0]
            max_similarity = np.max(sims)
            max_index = np.argmax(sims)

            if max_similarity < self.similarity_threshold:
                logger.info(f"Максимальное сходство {max_similarity:.2f} ниже порога {self.similarity_threshold}")
                return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]

            best_sentence = self.paragraphs[self.current_agent][max_index]
            if self.tokenizer:
                self._last_context_tokens = len(self.tokenizer.encode(best_sentence))
            logger.info(f"Выбран параграф с индексом {max_index}, сходство: {max_similarity:.2f}")
            return [Document(page_content=best_sentence)]

        except Exception as e:
            logger.error(f"Ошибка в _get_relevant_documents: {e}")
            return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        return self._get_relevant_documents(query)

    @property
    def last_context_tokens(self) -> int:
        return self._last_context_tokens

# --- Базовый промпт-шаблон для чата ---
base_instruction = "Ты — помощник, который строго отвечает только на основании предоставленного контекста и истории чата в одно предложение. Если контекста нет, отвечай на общие вопросы как дружелюбный бот (приветствия, прощания и т.д.)."

# --- RAG ---
retriever = ParagraphRetriever(
    paragraphs={},
    paragraph_embeddings={},
    embeddings_model=emb_model
)

# --- Функция для рендеринга чата в текст (с контекстом) ---
def render_chat_with_context(history: List[Dict[str, Any]], current_question: str, context: str, current_username: str) -> str:
    messages = [{"role": "Система", "content": base_instruction + ("\nКонтекст: " + context if context else "")}]
    for msg in history:
        username = msg.get("username")
        messages.append({"role": username, "content": msg["message"]})
    messages.append({"role": current_username, "content": current_question})
    prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages]) + "\nAI-помощник:"
    return prompt_text

# --- Функция для рендеринга только истории (для подсчёта токенов) ---
def render_history_only(history: List[Dict[str, Any]]) -> str:
    history_messages = [{"role": "Система", "content": base_instruction}]
    for msg in history:
        username = msg.get("username")
        history_messages.append({"role": username, "content": msg["message"]})
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history_messages])
    return history_str

# --- Функция для обработки запросов ---
def process_query(query: str, message_history: List[Dict[str, Any]] = None, current_username: str = "Пользователь", chat_id: str = None) -> Tuple[str, List[Dict[str, Any]]]:
    start_time = time.time()
    selected_agent = "none"
    status = "error"

    if message_history is None:
        message_history = []

    try:
        logger.info("Processing query", extra={
            "chat_id": chat_id,
            "username": current_username,
            "query_length": len(query),
            "history_length": len(message_history)
        })

        if not query.strip():
            status = "empty_query"
            ai_requests_total.labels(agent="none", status=status).inc()
            logger.warning("Empty query received", extra={"chat_id": chat_id})
            return "Введите корректный запрос.", message_history

        # Проверка на фразу "Передай запрос специалисту."
        query_emb = emb_model.encode(
            query,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        spech_phrase = "Передай запрос специалисту."
        phrase_emb = emb_model.encode(
            spech_phrase,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        sim = cosine_similarity([query_emb], [phrase_emb])[0][0]
        if sim >= 0.7:
            status = "escalated"
            selected_agent = "specialist"
            ai_requests_total.labels(agent=selected_agent, status=status).inc()
            ai_special_cases_total.labels(case_type="escalation").inc()

            answer = "Запрос передан специалисту. Пожалуйста, подождите."
            duration = time.time() - start_time

            logger.info("Запрос передан специалисту", extra={
                "chat_id": chat_id,
                "username": current_username,
                "similarity": float(sim),
                "duration": duration,
                "status": status
            })

            ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": answer})
            return answer, message_history

        # Проверка на ненормативную лексику
        profanity_phrases = [
            "дурак", "идиот", "глупый", "матерное слово",
            "ругательство", "похабщина"
        ]
        profanity_emb = emb_model.encode(
            profanity_phrases,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        profanity_sims = cosine_similarity([query_emb], profanity_emb)[0]
        max_profanity_sim = max(profanity_sims)
        max_profanity_idx = profanity_sims.argmax()
        
        logger.info(f"Ненормативная лексика - max_sim: {max_profanity_sim:.3f}, фраза: '{profanity_phrases[max_profanity_idx]}'")
        if max_profanity_sim >= 0.7:
            status = "profanity"
            selected_agent = "moderation"
            ai_requests_total.labels(agent=selected_agent, status=status).inc()
            ai_special_cases_total.labels(case_type="profanity").inc()

            answer = "Ведите себя культурно!"
            duration = time.time() - start_time

            logger.warning("Обнаружена ненормативная лексика", extra={
                "chat_id": chat_id,
                "username": current_username,
                "similarity": float(max_profanity_sim),
                "matched_phrase": profanity_phrases[max_profanity_idx],
                "duration": duration
            })

            ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": answer})
            return answer, message_history

        # Проверка на приветствия
        greeting_phrases = [
            "Ты кто?", "Ты бот?",
            "Привет.", "Здравствуйте.",
            "Как дела?",
            "Спасибо.",
            "Пока.", "До свидания."
        ]
        phrases_emb = emb_model.encode(
            greeting_phrases,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        similarities = cosine_similarity([query_emb], phrases_emb)[0]
        max_sim_idx = np.argmax(similarities)
        max_similarity = similarities[max_sim_idx]
        
        logger.info(f"Приветствие - max_sim: {max_similarity:.3f}, фраза: '{greeting_phrases[max_sim_idx]}'")

        if max_similarity >= 0.7:
            status = "greeting"
            selected_agent = "base_model"
            ai_special_cases_total.labels(case_type="greeting").inc()

            full_prompt = render_chat_with_context(message_history, query, "", current_username)

            hf_pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=base_tokenizer,
                max_new_tokens=150,
                temperature=0.1,
                top_p=0.95,
                repetition_penalty=1.1,
                return_full_text=False
            )

            generated = hf_pipeline(full_prompt)
            answer_text = generated[0]['generated_text'].strip()

            sentences = list(sentenize(answer_text))
            first_sentence = sentences[0].text if sentences else answer_text

            duration = time.time() - start_time
            ai_requests_total.labels(agent=selected_agent, status=status).inc()
            ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

            logger.info("Обработано приветствие", extra={
                "chat_id": chat_id,
                "username": current_username,
                "matched_phrase": greeting_phrases[max_sim_idx],
                "similarity": float(max_similarity),
                "duration": duration,
                "answer_length": len(first_sentence)
            })

            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": first_sentence})
            return first_sentence, message_history

        # Выбор агента
        selected_tokenizer, selected_model, file_path = retriever.select_agent(query)
        if selected_tokenizer is None or selected_model is None:
            status = "no_agent"
            ai_requests_total.labels(agent="none", status=status).inc()
            ai_special_cases_total.labels(case_type="no_context").inc()

            duration = time.time() - start_time
            ai_request_duration_seconds.labels(agent="none").observe(duration)

            logger.warning("Не удалось выбрать агента", extra={
                "chat_id": chat_id,
                "username": current_username,
                "query": query[:100],
                "duration": duration
            })

            return "Не понял вопрос, уточните, пожалуйста!", message_history

        # Устанавливаем текущего агента
        retriever.current_agent = os.path.basename(file_path).split(".")[0]
        selected_agent = retriever.current_agent

        logger.info("Выбран агент", extra={
            "chat_id": chat_id,
            "agent": selected_agent
        })
        retriever.paragraphs[retriever.current_agent], retriever.paragraph_embeddings[retriever.current_agent] = retriever.load_paragraphs(file_path)

        # Устанавливаем токенизатор для retriever
        retriever.tokenizer = selected_tokenizer
        question_tokens = len(selected_tokenizer.encode(query))
        
        # Предварительный расчёт истории
        history_str = render_history_only(message_history)
        history_tokens = len(selected_tokenizer.encode(history_str))
        
        # Устанавливаем лимиты
        retriever.set_dynamic_limits(question_tokens=question_tokens, history_tokens=history_tokens, max_total_tokens=8192)

        docs = retriever._get_relevant_documents(query)
        if docs[0].page_content == "Не понял вопрос, уточните, пожалуйста!":
            status = "no_context"
            ai_requests_total.labels(agent=selected_agent, status=status).inc()
            ai_special_cases_total.labels(case_type="no_context").inc()

            duration = time.time() - start_time
            ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

            logger.warning("Контекст не найден", extra={
                "chat_id": chat_id,
                "agent": selected_agent,
                "duration": duration
            })

            answer = "Не понял вопрос, уточните, пожалуйста!"
            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": answer})
            return answer, message_history

        context = docs[0].page_content
        context_tokens = retriever.last_context_tokens if context else 0

        # Логируем использование токенов
        ai_tokens_used.labels(token_type="question").observe(question_tokens)
        ai_tokens_used.labels(token_type="history").observe(history_tokens)
        ai_tokens_used.labels(token_type="context").observe(context_tokens)

        logger.info(f"Токены (до обрезки): история={history_tokens}, вопрос={question_tokens}, контекст={context_tokens}")

        # Вычисляем требуемые токены
        max_total_tokens = 8192
        reserved = retriever.reserved_output_tokens + 100
        available_input = max_total_tokens - reserved
        required = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens

        # Обрезка истории
        history_truncated = False
        while required > available_input and len(message_history) >= 2:
            removed_user = message_history.pop(0)
            removed_ai = message_history.pop(0)
            history_truncated = True
            ai_history_truncation_total.inc()

            logger.info(f"Обрезано старое сообщение из истории: {removed_user.get('message', '')[:50]}...")
            history_str = render_history_only(message_history)
            history_tokens = len(selected_tokenizer.encode(history_str))
            required = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens

        if history_truncated:
            logger.info("История обрезана", extra={
                "chat_id": chat_id,
                "new_history_length": len(message_history),
                "new_history_tokens": history_tokens
            })

        # Обрезка контекста как fallback
        if required > available_input and context:
            max_context_tokens = available_input - retriever.prompt_token_len - history_tokens - question_tokens
            encoded_context = selected_tokenizer.encode(context)
            if len(encoded_context) > max_context_tokens:
                truncated_tokens = encoded_context[:max_context_tokens]
                context = selected_tokenizer.decode(truncated_tokens, skip_special_tokens=True)
                context_tokens = len(truncated_tokens)
                logger.warning(f"Контекст обрезан как fallback до {context_tokens} токенов")

        logger.info(f"Токены (после обрезки): история={history_tokens}, вопрос={question_tokens}, контекст={context_tokens}")

        # Pipeline для генерации
        hf_pipeline = pipeline(
            "text-generation",
            model=selected_model,
            tokenizer=selected_tokenizer,
            max_new_tokens=retriever.reserved_output_tokens,
            temperature=0.1,
            top_p=0.95,
            repetition_penalty=1.1,
            return_full_text=False
        )

        full_prompt = render_chat_with_context(message_history, query, context, current_username)
        
        generated = hf_pipeline(full_prompt)
        answer_text = generated[0]['generated_text'].strip()
        
        sentences = list(sentenize(answer_text))
        first_sentence = sentences[0].text if sentences else answer_text

        # Проверка сходства ответа с контекстом
        if context:
            answer_emb = emb_model.encode(first_sentence, prompt_name="paraphrase", convert_to_numpy=True, normalize_embeddings=True)
            context_emb = emb_model.encode(context, prompt_name="paraphrase", convert_to_numpy=True, normalize_embeddings=True)
            similarity = cosine_similarity([answer_emb], [context_emb])[0][0]

            ai_context_similarity.observe(float(similarity))

            if similarity < 0.5:
                status = "escalated"
                ai_requests_total.labels(agent=selected_agent, status=status).inc()
                ai_special_cases_total.labels(case_type="low_similarity").inc()

                first_sentence = "Запрос передан специалисту. Пожалуйста, подождите."

                duration = time.time() - start_time
                ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

                logger.warning("Низкая схожесть ответа с контекстом", extra={
                    "chat_id": chat_id,
                    "agent": selected_agent,
                    "similarity": float(similarity),
                    "duration": duration
                })
            else:
                status = "success"
                ai_requests_total.labels(agent=selected_agent, status=status).inc()

                duration = time.time() - start_time
                total_tokens = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens
                ai_tokens_used.labels(token_type="total").observe(total_tokens)
                ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

                logger.info("Запрос успешно обработан", extra={
                    "chat_id": chat_id,
                    "agent": selected_agent,
                    "username": current_username,
                    "context_similarity": float(similarity),
                    "duration": duration,
                    "total_tokens": total_tokens,
                    "answer_length": len(first_sentence)
                })

        message_history.append({"username": current_username, "message": query})
        message_history.append({"answer": first_sentence})

        return first_sentence, message_history

    except Exception as e:
        duration = time.time() - start_time
        ai_requests_total.labels(agent=selected_agent, status="error").inc()
        ai_request_duration_seconds.labels(agent=selected_agent).observe(duration)

        logger.error("Ошибка при обработке запроса", extra={
            "chat_id": chat_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration": duration
        }, exc_info=True)

        return "Произошла ошибка при обработке запроса.", message_history

# --- RabbitMQ интеграция ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')
QUEUE_IN = os.getenv('QUEUE_IN')
QUEUE_OUT = os.getenv('QUEUE_OUT')
BOT_USERNAME = "AI-помощник"

def callback(ch, method, properties, body):
    is_manager = False  # Локальная переменная
    try:
        data = json.loads(body)
        query = data.get('message', '')
        message_history = data.get('messageHistory', [])
        chat_id = data.get('chatId', None)
        current_username = "Пользователь"
        if 'username' in data:
            current_username = data['username']
        elif message_history and 'username' in message_history[-1]:
            current_username = message_history[-1]['username']
        
        logger.info(f"Получен запрос из RabbitMQ: {query}")
        
        answer, new_history = process_query(query, message_history, current_username, chat_id)

        if answer == "Запрос передан специалисту. Пожалуйста, подождите.":
            is_manager = True
        
        response = {
            'chatId': chat_id,
            'answer': answer,
            'botUsername': BOT_USERNAME,
            'isManager': is_manager
        }

        ch.basic_publish(exchange='', routing_key=QUEUE_OUT, body=json.dumps(response))
        logger.info(f"Отправлен ответ в {QUEUE_OUT}: {answer}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

if __name__ == "__main__":
    # Запускаем сервер метрик Prometheus на порту 1234
    metrics_port = int(os.getenv('METRICS_PORT', 1234))
    start_metrics_server(port=metrics_port)
    logger.info(f"Сервер метрик Prometheus запущен на порту {metrics_port}")

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_IN, durable=True)
    channel.queue_declare(queue=QUEUE_OUT, durable=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_IN, on_message_callback=callback)

    logger.info("Ожидание сообщений из RabbitMQ. Для выхода нажмите CTRL+C")
    channel.start_consuming()