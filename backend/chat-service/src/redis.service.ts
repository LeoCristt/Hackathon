import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import Redis from 'ioredis';

interface ChatMessage {
  sequence: number;
  username: string;
  message: string;
  timestamp: string;
  chatId: string;
}

@Injectable()
export class RedisService implements OnModuleInit, OnModuleDestroy {
  private client: Redis;
  private readonly MAX_MESSAGES_PER_CHAT = parseInt(process.env.REDIS_MAX_MESSAGES || '50', 10);
  private readonly REDIS_URL = process.env.REDIS_URL || 'redis://redis:6379';

  async onModuleInit() {
    await this.connect();
  }

  async onModuleDestroy() {
    await this.disconnect();
  }

  private async connect() {
    console.log('Подключение к Redis:', this.REDIS_URL);

    this.client = new Redis(this.REDIS_URL, {
      maxRetriesPerRequest: 3,
      retryStrategy: (times: number) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
    });

    this.client.on('connect', () => {
      console.log('Успешно подключен к Redis');
    });

    this.client.on('error', (err: Error) => {
      console.error('Ошибка Redis:', err.message);
    });

    this.client.on('close', () => {
      console.log('Соединение с Redis закрыто');
    });
  }

  /**
   * Добавляет сообщение в кэш чата
   * Использует Redis List для хранения последних N сообщений
   */
  async cacheMessage(chatId: string, message: ChatMessage): Promise<void> {
    try {
      const key = `chat:${chatId}:messages`;
      const messageJson = JSON.stringify(message);

      await this.client.rpush(key, messageJson);
      await this.client.ltrim(key, -this.MAX_MESSAGES_PER_CHAT, -1);
      await this.client.expire(key, 86400);

      console.log(`Сообщение закэширован в Redis для чата ${chatId}`);
    } catch (error) {
      console.error('Ошибка кэширования сообщения:', error);
    }
  }

  /**
   * Получает историю сообщений для чата
   * @param chatId - ID чата
   * @param limit - Количество последних сообщений (по умолчанию все)
   */
  async getMessageHistory(chatId: string, limit?: number): Promise<ChatMessage[]> {
    try {
      const key = `chat:${chatId}:messages`;
      const count = limit || this.MAX_MESSAGES_PER_CHAT;

      // Получаем последние N сообщений
      const messages = await this.client.lrange(key, -count, -1);

      const parsedMessages = messages.map((msg) => JSON.parse(msg));

      console.log(`Получено ${parsedMessages.length} сообщений из кэша для чата ${chatId}`);

      return parsedMessages;
    } catch (error) {
      console.error('Ошибка получения истории сообщений:', error);
      return [];
    }
  }

  /**
   * Очищает историю сообщений для чата
   */
  async clearChatHistory(chatId: string): Promise<void> {
    try {
      const key = `chat:${chatId}:messages`;
      await this.client.del(key);
      console.log(`История сообщений очищена для чата ${chatId}`);
    } catch (error) {
      console.error('Ошибка очистки истории:', error);
    }
  }

  /**
   * Получает количество сообщений в кэше для чата
   */
  async getMessageCount(chatId: string): Promise<number> {
    try {
      const key = `chat:${chatId}:messages`;
      return await this.client.llen(key);
    } catch (error) {
      console.error('Ошибка получения количества сообщений:', error);
      return 0;
    }
  }

  /**
   * Получает следующий порядковый номер для сообщения в чате
   * Использует атомарный INCR для обеспечения уникальности
   */
  async getNextSequence(chatId: string): Promise<number> {
    try {
      const key = `chat:${chatId}:sequence`;
      const sequence = await this.client.incr(key);

      // Устанавливаем TTL на 7 дней для счетчика
      await this.client.expire(key, 604800);

      console.log(`Получен sequence ${sequence} для чата ${chatId}`);
      return sequence;
    } catch (error) {
      console.error('Ошибка получения sequence:', error);
      // В случае ошибки возвращаем timestamp как fallback
      return Date.now();
    }
  }

  /**
   * Устанавливает флаг требования менеджера для чата
   */
  async setManagerRequired(chatId: string, required: boolean): Promise<void> {
    try {
      const key = `chat:${chatId}:manager_required`;
      if (required) {
        await this.client.set(key, '1');
        await this.client.expire(key, 86400); // TTL 24 часа
        console.log(`Флаг manager_required установлен для чата ${chatId}`);
      } else {
        await this.client.del(key);
        console.log(`Флаг manager_required снят для чата ${chatId}`);
      }
    } catch (error) {
      console.error('Ошибка установки флага manager_required:', error);
    }
  }

  /**
   * Проверяет, требуется ли менеджер для чата
   */
  async isManagerRequired(chatId: string): Promise<boolean> {
    try {
      const key = `chat:${chatId}:manager_required`;
      const value = await this.client.get(key);
      return value === '1';
    } catch (error) {
      console.error('Ошибка проверки флага manager_required:', error);
      return false;
    }
  }

  private async disconnect() {
    if (this.client) {
      await this.client.quit();
      console.log('Отключен от Redis');
    }
  }
}
