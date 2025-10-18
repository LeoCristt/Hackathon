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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                self.paragraph_embeddings[agent] = []
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            paragraphs = split_into_paragraphs(text)
            logger.info(f"Разбито на {len(paragraphs)} абзацев из файла {file_path}")

            # Проверка, есть ли эмбеддинги в ChromaDB
            existing_ids = collection.get(where={"agent": agent})["ids"]
            if not existing_ids:
                # Вычисление эмбеддингов
                paragraph_embeddings = self.embeddings_model.encode(
                    paragraphs,
                    prompt_name="search_document",
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                # Сохранение в ChromaDB
                for i, (paragraph, embedding) in enumerate(zip(paragraphs, paragraph_embeddings)):
                    collection.add(
                        documents=[paragraph],
                        embeddings=[embedding.tolist()],
                        ids=[f"{agent}_{i}"],
                        metadatas=[{"agent": agent}]
                    )
                logger.info(f"Сохранены эмбеддинги для {agent} в ChromaDB")
                self.paragraphs[agent] = paragraphs
                self.paragraph_embeddings[agent] = paragraph_embeddings
            else:
                # Загрузка из ChromaDB
                results = collection.get(where={"agent": agent})
                self.paragraphs[agent] = results["documents"]
                self.paragraph_embeddings[agent] = np.array(results["embeddings"])
                logger.info(f"Загружено {len(self.paragraphs[agent])} абзацев для агента {agent} из ChromaDB")

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
        query_emb = self.embeddings_model.encode(
            query,
            prompt_name="search_query",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        sims = cosine_similarity([query_emb], self.paragraph_embeddings[self.current_agent])[0]
        max_similarity = max(sims)
        max_index = sims.argmax()
        
        if max_similarity < self.similarity_threshold:
            return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]
        
        best_sentence = self.paragraphs[self.current_agent][max_index]
        self._last_context_tokens = len(self.tokenizer.encode(best_sentence))
        return [Document(page_content=best_sentence)]

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
    if message_history is None:
        message_history = []
    
    try:
        if not query.strip():
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
            answer = "Запрос передан специалисту. Пожалуйста, подождите."
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
            answer = "Ведите себя культурно!"
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
            
            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": first_sentence})
            return first_sentence, message_history

        # Выбор агента
        selected_tokenizer, selected_model, file_path = retriever.select_agent(query)
        if selected_tokenizer is None or selected_model is None:
            return "Не понял вопрос, уточните, пожалуйста!", message_history

        # Устанавливаем текущего агента
        retriever.current_agent = os.path.basename(file_path).split(".")[0]
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
            answer = "Не понял вопрос, уточните, пожалуйста!"
            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": answer})
            return answer, message_history
        
        context = docs[0].page_content
        context_tokens = retriever.last_context_tokens if context else 0
        logger.info(f"Токены (до обрезки): история={history_tokens}, вопрос={question_tokens}, контекст={context_tokens}")

        # Вычисляем требуемые токены
        max_total_tokens = 8192
        reserved = retriever.reserved_output_tokens + 100
        available_input = max_total_tokens - reserved
        required = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens

        # Обрезка истории
        while required > available_input and len(message_history) >= 2:
            removed_user = message_history.pop(0)
            removed_ai = message_history.pop(0)
            logger.info(f"Обрезано старое сообщение из истории: {removed_user.get('message', '')[:50]}...")
            history_str = render_history_only(message_history)
            history_tokens = len(selected_tokenizer.encode(history_str))
            required = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens

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
            
            if similarity < 0.5:
                first_sentence = "Запрос передан специалисту. Пожалуйста, подождите."

        message_history.append({"username": current_username, "message": query})
        message_history.append({"answer": first_sentence})

        return first_sentence, message_history

    except Exception as e:
        logger.error(f"Ошибка: {e}")
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
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    
    channel.queue_declare(queue=QUEUE_IN, durable=True)
    channel.queue_declare(queue=QUEUE_OUT, durable=True)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_IN, on_message_callback=callback)
    
    logger.info("Ожидание сообщений из RabbitMQ. Для выхода нажмите CTRL+C")
    channel.start_consuming()