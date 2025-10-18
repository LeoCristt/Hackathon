import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import * as amqp from 'amqp-connection-manager';
import { ChannelWrapper } from 'amqp-connection-manager';

interface AIRequest {
  chatId: string;
  message: string;
  messageHistory: any[];
  aiId?: string;
}

interface AIResponse {
  chatId: string;
  answer: string;
  botUsername: string;
}

@Injectable()
export class RabbitMQService implements OnModuleInit, OnModuleDestroy {
  private connection: amqp.AmqpConnectionManager;
  private channelWrapper: ChannelWrapper;

  // Очереди для микросервиса БД
  private readonly DB_QUEUE = 'db_messages';

  // Очереди для AI-сервиса
  private readonly AI_REQUEST_QUEUE = 'ai_requests';
  private readonly AI_RESPONSE_QUEUE = 'ai_response';

  private readonly RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@rabbitmq:5672';
  private aiResponseCallback: ((response: AIResponse) => void) | null = null;

  async onModuleInit() {
    await this.connect();
  }

  async onModuleDestroy() {
    await this.disconnect();
  }

  private async connect() {
    console.log('Подключение к RabbitMQ:', this.RABBITMQ_URL);

    this.connection = amqp.connect([this.RABBITMQ_URL]);

    this.connection.on('connect', () => {
      console.log('Успешно подключен к RabbitMQ');
    });

    this.connection.on('disconnect', (err: any) => {
      console.log('Отключен от RabbitMQ:', err?.message || 'неизвестная ошибка');
    });

    this.channelWrapper = this.connection.createChannel({
      json: true,
      setup: async (channel: amqp.Channel) => {
        // Очереди уже созданы через rabbitmq-definitions.json в docker-compose
        // Просто проверяем их наличие (assertQueue с passive:true только проверяет, не создает)
        await channel.checkQueue(this.DB_QUEUE);
        console.log(`Очередь для БД "${this.DB_QUEUE}" найдена`);

        await channel.checkQueue(this.AI_REQUEST_QUEUE);
        await channel.checkQueue(this.AI_RESPONSE_QUEUE);
        console.log(`Очереди для AI сервиса найдены`);

        // Подписываемся на ответы от AI агента
        await channel.consume(this.AI_RESPONSE_QUEUE, (msg) => {
          if (msg !== null) {
            const response: AIResponse = JSON.parse(msg.content.toString());
            console.log('Получен ответ от AI агента:', response);

            if (this.aiResponseCallback) {
              this.aiResponseCallback(response);
            }

            channel.ack(msg);
          }
        });

        console.log(`Подписан на очередь ответов от AI`);
      },
    });
  }

  /**
   * Отправляет одно сообщение в очередь БД для сохранения
   */
  async sendMessageToDB(message: any): Promise<boolean> {
    try {
      await this.channelWrapper.sendToQueue(
        this.DB_QUEUE,
        message,
        {
          persistent: true,
          contentType: 'application/json'
        } as any
      );
      console.log('Сообщение отправлено в БД сервис:', message);
      return true;
    } catch (error) {
      console.error('Ошибка отправки сообщения в БД:', error);
      return false;
    }
  }

  /**
   * Отправляет запрос к AI сервису
   * @param chatId - ID чата
   * @param message - Текущее сообщение пользователя
   * @param messageHistory - История последних сообщений из Redis
   * @param aiId - ID AI модели (опционально)
   */
  async sendToAI(request: AIRequest): Promise<boolean> {
    try {
      await this.channelWrapper.sendToQueue(
        this.AI_REQUEST_QUEUE,
        request,
        {
          persistent: true,
          contentType: 'application/json'
        } as any
      );
      console.log('Запрос отправлен AI сервису:', {
        chatId: request.chatId,
        message: request.message,
        historyLength: request.messageHistory.length,
        aiId: request.aiId || 'default'
      });
      return true;
    } catch (error) {
      console.error('Ошибка отправки запроса в AI:', error);
      return false;
    }
  }

  /**
   * Устанавливает callback для обработки ответов от AI
   */
  setAIResponseCallback(callback: (response: AIResponse) => void) {
    this.aiResponseCallback = callback;
  }

  private async disconnect() {
    if (this.channelWrapper) {
      await this.channelWrapper.close();
    }
    if (this.connection) {
      await this.connection.close();
    }
    console.log('Отключен от RabbitMQ');
  }
}
