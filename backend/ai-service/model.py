import torch
import numpy as np
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, PreTrainedTokenizerBase
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Any
import logging
from peft import PeftModel
from sentence_transformers import SentenceTransformer
from razdel import sentenize
from numpy.typing import NDArray
import os
import pika
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Используемое устройство: {device}")

# --- Разделение на абзацы ---
def split_into_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n', text) if p.strip()]
    return paragraphs

base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "Сеть.txt")

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

paragraphs = split_into_paragraphs(text)
logger.info(f"Разбито на {len(paragraphs)} абзацев.")

local_emb_model_path = os.path.join(base_dir, "frida_embedding_model")

emb_model = SentenceTransformer(local_emb_model_path, device=device)
paragraph_embeddings = emb_model.encode(
    paragraphs,
    prompt_name="search_document",
    convert_to_numpy=True,
    normalize_embeddings=True
)

# --- Модель и токенизатор ---
model = AutoModelForCausalLM.from_pretrained(os.path.join(base_dir, "quantized_model"))
tokenizer = AutoTokenizer.from_pretrained(os.path.join(base_dir, "Сеть/best_model"))

# --- LLM ---
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = PeftModel.from_pretrained(model, os.path.join(base_dir, "Сеть/best_model"))

class ParagraphRetriever(BaseRetriever):
    paragraphs: List[str]
    paragraph_embeddings: List[NDArray]
    embeddings_model: SentenceTransformer
    tokenizer: PreTrainedTokenizerBase
    similarity_threshold: float = 0.25
    prompt_token_len: int = 0
    history_tokens: int = 0
    question_tokens: int = 0
    reserved_output_tokens: int = 150

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_context_tokens = 0
        # Оценка базового шаблона (system + borders)
        template_sample = "Ты — помощник. Используй историю и контекст.\n\n"
        self.prompt_token_len = len(self.tokenizer.encode(template_sample))

    def set_dynamic_limits(self, question_tokens: int, history_tokens: int, max_total_tokens: int = 8192):
        self.question_tokens = question_tokens
        self.history_tokens = history_tokens
        # Теперь не ограничиваем контекст заранее; обрезка истории происходит позже

    def _get_relevant_documents(self, query: str) -> List[Document]:
        query_emb = self.embeddings_model.encode(
            query,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        spech_phrase = "Передай запрос специалисту."
        phrase_emb = self.embeddings_model.encode(
            spech_phrase,
            prompt_name="paraphrase",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        sim = cosine_similarity([query_emb], [phrase_emb])
        if sim >= 0.7:
            # Нашли подходящую фразу — прерываем
            return [Document(page_content=spech_phrase)]
        # Обычный поиск, если не greeting или sim < 0.5
        query_emb = self.embeddings_model.encode(
            query,
            prompt_name="search_query",
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        sims = cosine_similarity([query_emb], self.paragraph_embeddings)[0]
        max_similarity = max(sims)
        max_index = sims.argmax()
        
        if max_similarity < self.similarity_threshold:
            # Новая проверка для приветствий/прощаний и т.д.
            greeting_phrases = [
                "Ты кто?", "Ты бот?",
                "Привет.", "Здравствуйте.",
                "Как дела?",
                "Спасибо.",
                "Пока.", "До свидания."
            ]

            # Проверяем, содержит ли запрос хотя бы одно из ключевых слов
            # Эмбеддинг запроса
            query_emb = self.embeddings_model.encode(
                query,
                prompt_name="paraphrase",
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # Эмбеддинги фраз
            phrases_emb = self.embeddings_model.encode(
                greeting_phrases,
                prompt_name="paraphrase",
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # Проверяем каждую фразу отдельно
            for phrase, phrase_emb in zip(greeting_phrases, phrases_emb):
                sim = cosine_similarity([query_emb], [phrase_emb])[0][0]
                if sim >= 0.7:
                    # Нашли подходящую фразу — прерываем
                    return [Document(page_content=phrase)]
            return [Document(page_content="Не понял вопрос, уточните, пожалуйста!")]
        
        best_sentence = self.paragraphs[max_index]
        
        # Не обрезаем контекст здесь; обрезка только если после обрезки истории всё равно не влезает (в process_query)
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
    paragraphs=paragraphs,
    paragraph_embeddings=paragraph_embeddings,
    embeddings_model=emb_model,
    tokenizer=tokenizer
)

# --- Функция для рендеринга чата в текст (с контекстом) ---
def render_chat_with_context(history: List[Dict[str, Any]], current_question: str, context: str, current_username: str) -> str:
    messages = [{"role": "Система", "content": base_instruction + ("\nКонтекст: " + context if context else "")}]
    
    for i, msg in enumerate(history):
        if i % 2 == 0:
            # Пользователь
            username = msg.get("username", "Пользователь")
            messages.append({"role": username, "content": msg["message"]})
        else:
            # AI
            messages.append({"role": "AI-помощник", "content": msg["answer"]})
    
    messages.append({"role": current_username, "content": current_question})
    
    prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages]) + "\nAI-помощник:"
    
    return prompt_text

# --- Функция для рендеринга только истории (для подсчёта токенов) ---
def render_history_only(history: List[Dict[str, Any]]) -> str:
    history_messages = [{"role": "Система", "content": base_instruction}]
    for i, msg in enumerate(history):
        if i % 2 == 0:
            # Пользователь
            username = msg.get("username", "Пользователь")
            history_messages.append({"role": username, "content": msg["message"]})
        else:
            # AI
            history_messages.append({"role": "AI-помощник", "content": msg["answer"]})
    
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history_messages])
    
    return history_str

# --- Функция для обработки запросов ---
def process_query(query: str, message_history: List[Dict[str, Any]] = None, current_username: str = "Пользователь", chat_id: str = None) -> Tuple[str, List[Dict[str, Any]]]:
    if message_history is None:
        message_history = []
    
    try:
        if not query.strip():
            return "Введите корректный запрос.", message_history

        question_tokens = len(tokenizer.encode(query))
        
        # Предварительный расчёт истории
        history_str = render_history_only(message_history)
        history_tokens = len(tokenizer.encode(history_str))
        
        # Устанавливаем лимиты (без обрезки контекста)
        retriever.set_dynamic_limits(question_tokens=question_tokens, history_tokens=history_tokens, max_total_tokens=8192)

        docs = retriever._get_relevant_documents(query)
        if docs[0].page_content == "Не понял вопрос, уточните, пожалуйста!":
            answer = "Не понял вопрос, уточните, пожалуйста!"
            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": answer})
            return answer, message_history
        elif docs[0].page_content == "Передай запрос специалисту.":
            answer = "Запрос передан специалисту. Пожалуйста, подождите."
            message_history.append({"username": current_username, "message": query})
            message_history.append({"answer": answer})
            return answer, message_history
        
        context = docs[0].page_content
        context_tokens = retriever.last_context_tokens if context else 0
        logger.info(f"Токены (до обрезки): история={history_tokens}, вопрос={question_tokens}, контекст={context_tokens}")

        # Вычисляем требуемые токены
        max_total_tokens = 8192
        reserved = retriever.reserved_output_tokens + 100  # Запас
        available_input = max_total_tokens - reserved
        required = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens

        # Если переполнение — обрезаем историю (удаляем старые пары: user + ai)
        while required > available_input and len(message_history) >= 2:
            # Удаляем самое старое сообщение пользователя и ответ (пара)
            removed_user = message_history.pop(0)
            removed_ai = message_history.pop(0)
            logger.info(f"Обрезано старое сообщение из истории: {removed_user.get('message', '')[:50]}...")
            
            # Пересчитываем историю
            history_str = render_history_only(message_history)
            history_tokens = len(tokenizer.encode(history_str))
            required = retriever.prompt_token_len + history_tokens + question_tokens + context_tokens

        # Если после обрезки истории всё равно не влезает (редкий случай, если контекст огромный) — обрезаем контекст как fallback
        if required > available_input and context:
            max_context_tokens = available_input - retriever.prompt_token_len - history_tokens - question_tokens
            encoded_context = tokenizer.encode(context)
            if len(encoded_context) > max_context_tokens:
                truncated_tokens = encoded_context[:max_context_tokens]
                context = tokenizer.decode(truncated_tokens, skip_special_tokens=True)
                context_tokens = len(truncated_tokens)
                logger.warning(f"Контекст обрезан как fallback до {context_tokens} токенов (история пуста или минимальна)")
        
        logger.info(f"Токены (после обрезки): история={history_tokens}, вопрос={question_tokens}, контекст={context_tokens}")

        # Pipeline для генерации
        hf_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
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

        # Проверка сходства только если контекст не пустой
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
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')  # Измените на ваш хост
QUEUE_IN = os.getenv('QUEUE_IN')     # Очередь для входящих запросов
QUEUE_OUT = os.getenv('QUEUE_OUT')  # Очередь для исходящих ответов
BOT_USERNAME = "AI-помощник"

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        query = data.get('message', '')
        message_history = data.get('messageHistory', [])
        chat_id = data.get('chatId', None)
        # Предполагаем, что текущий username приходит в data, или из последнего user сообщения
        current_username = "Пользователь"
        if 'username' in data:
            current_username = data['username']
        elif message_history and 'username' in message_history[-1]:
            current_username = message_history[-1]['username']
        
        logger.info(f"Получен запрос из RabbitMQ: {query}")
        
        answer, new_history = process_query(query, message_history, current_username, chat_id)
        print(answer)
        print(new_history)
        print(current_username)
        print(chat_id)
        
        response = {
            'chatId': chat_id,
            'answer': answer,
            'botUsername': BOT_USERNAME
        }

        print(response)
        
        # Отправка ответа
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