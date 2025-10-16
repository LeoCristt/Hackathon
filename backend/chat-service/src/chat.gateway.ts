import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  MessageBody,
  ConnectedSocket,
  OnGatewayConnection,
  OnGatewayDisconnect,
  OnGatewayInit,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { RabbitMQService } from './rabbitmq.service';
import { RedisService } from './redis.service';

interface ChatMessage {
  messageId: string;
  sequence: number;
  username: string;
  message: string;
  timestamp: string;
  chatId: string;
}

interface UserInfo {
  chatId: string;
  username: string;
}

@WebSocketGateway({
  cors: {
    origin: '*',
  },
})
export class ChatGateway implements OnGatewayConnection, OnGatewayDisconnect, OnGatewayInit {
  @WebSocketServer()
  server: Server;

  private connectedUsers = new Map<string, UserInfo>();
  private chatRooms = new Map<string, Set<string>>(); // chatId -> Set<socketId>

  constructor(
    private readonly rabbitMQService: RabbitMQService,
    private readonly redisService: RedisService,
  ) {}

  afterInit() {
    // Подписываемся на ответы от AI агента
    this.rabbitMQService.setAIResponseCallback((response) => {
      this.handleAIResponse(response);
    });
    console.log('✅ ChatGateway инициализирован, подписка на AI ответы настроена');
  }

  private async handleAIResponse(response: { chatId: string; response: string }) {
    const { chatId, response: aiMessage } = response;

    console.log('\n🎯 ═══ ПОЛУЧЕН ОТВЕТ ОТ AI СЕРВИСА ═══');
    console.log('Очередь: ai_responses');
    console.log('Chat ID:', chatId);
    console.log('Ответ AI:', aiMessage);
    console.log('Полные данные:', JSON.stringify(response, null, 2));

    const messageId = `${chatId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Получаем следующий sequence number из Redis (атомарно)
    const sequence = await this.redisService.getNextSequence(chatId);

    const chatMessage: ChatMessage = {
      messageId,
      sequence,
      username: 'AI Ассистент',
      message: aiMessage,
      timestamp: new Date().toISOString(),
      chatId,
    };

    console.log('\n📝 Сформированное сообщение AI:');
    console.log('  Message ID:', messageId);
    console.log('  Sequence:', sequence);
    console.log('  Username:', 'AI Ассистент');

    // Кэшируем ответ AI в Redis
    await this.redisService.cacheMessage(chatId, chatMessage);
    console.log('✅ Ответ AI закэширован в Redis');

    // Сохраняем ответ AI в БД через RabbitMQ
    console.log('\n📦 ═══ ОТПРАВКА ОТВЕТА AI В БД ═══');
    console.log('Очередь: db_messages');
    console.log('Данные:', JSON.stringify(chatMessage, null, 2));
    await this.rabbitMQService.sendMessageToDB(chatMessage);
    console.log('✅ Ответ AI отправлен в БД');

    // Отправляем ответ AI всем участникам чата через WebSocket
    const chatSockets = this.chatRooms.get(chatId);
    if (chatSockets) {
      console.log('\n🌐 Отправка ответа AI через WebSocket');
      console.log('  Количество подключенных клиентов:', chatSockets.size);
      chatSockets.forEach(socketId => {
        this.server.to(socketId).emit('message', chatMessage);
      });
      console.log('✅ Ответ AI отправлен всем участникам чата\n');
    } else {
      console.log('⚠️ Нет подключенных клиентов в чате', chatId, '\n');
    }
  }

  handleConnection(client: Socket) {
    console.log(`🔗 Клиент подключен: ${client.id}`);
  }

  handleDisconnect(client: Socket) {
    const userInfo = this.connectedUsers.get(client.id);

    if (userInfo) {
      const { username, chatId } = userInfo;

      // Удаляем из комнаты чата
      if (chatId && this.chatRooms.has(chatId)) {
        this.chatRooms.get(chatId)!.delete(client.id);

        // Если комната пуста, удаляем её
        if (this.chatRooms.get(chatId)!.size === 0) {
          this.chatRooms.delete(chatId);
        }
      }

      this.connectedUsers.delete(client.id);
      console.log(`🔌 Клиент отключен: ${client.id} (${username})`);
    }
  }

  @SubscribeMessage('join')
  async handleJoin(
    @MessageBody() data: { username?: string; chatId?: string },
    @ConnectedSocket() client: Socket,
  ) {
    const chatId = data.chatId || 'default';
    // Если username не передан - это обычный пользователь (аноним)
    // Если передан - это менеджер или другая роль
    const username = data.username || 'Пользователь';

    const userInfo: UserInfo = {
      username,
      chatId,
    };

    this.connectedUsers.set(client.id, userInfo);

    // Добавляем пользователя в комнату чата
    if (!this.chatRooms.has(chatId)) {
      this.chatRooms.set(chatId, new Set());
    }
    this.chatRooms.get(chatId)!.add(client.id);

    console.log(`👤 ${username} присоединился к чату ${chatId} (${client.id})`);

    // Получаем историю сообщений из Redis
    const messageHistory = await this.redisService.getMessageHistory(chatId);

    console.log(`📚 Отправка истории сообщений (${messageHistory.length} шт.) для ${username}`);

    // Отправляем историю только этому клиенту
    if (messageHistory.length > 0) {
      client.emit('history', messageHistory);
    }

    return {
      status: 'ok',
      message: 'Успешно присоединились к чату',
      chatId,
      username,
      historyCount: messageHistory.length,
    };
  }

  @SubscribeMessage('message')
  async handleMessage(
    @MessageBody() data: { message: string; aiId?: string },
    @ConnectedSocket() client: Socket,
  ) {
    const userInfo = this.connectedUsers.get(client.id);
    if (!userInfo) {
      return { status: 'error', message: 'Пользователь не найден' };
    }

    const { username, chatId } = userInfo;
    const timestamp = new Date().toISOString();
    const messageId = `${chatId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Получаем следующий sequence number из Redis
    const sequence = await this.redisService.getNextSequence(chatId);

    const chatMessage: ChatMessage = {
      messageId,
      sequence,
      username,
      message: data.message,
      timestamp,
      chatId,
    };

    console.log(`💬 [${messageId}] #${sequence} Сообщение от ${username} в чате ${chatId}: ${data.message}`);

    // 1. Отправляем сообщение всем участникам чата через WebSocket
    const chatSockets = this.chatRooms.get(chatId);
    if (chatSockets) {
      chatSockets.forEach(socketId => {
        this.server.to(socketId).emit('message', chatMessage);
      });
    }

    // 2. Кэшируем сообщение в Redis
    await this.redisService.cacheMessage(chatId, chatMessage);

    // 3. Отправляем сообщение в БД для сохранения (по одному сообщению)
    console.log('\n📦 ═══ ОТПРАВКА В БД СЕРВИС ═══');
    console.log('Очередь: db_messages');
    console.log('Данные:', JSON.stringify(chatMessage, null, 2));
    await this.rabbitMQService.sendMessageToDB(chatMessage);
    console.log('✅ Сообщение отправлено в БД\n');

    // 4. Получаем историю сообщений из Redis
    const messageHistory = await this.redisService.getMessageHistory(chatId);

    // 5. Отправляем на AI-сервис: сообщение + история + chatId + aiId
    const aiRequest = {
      chatId,
      message: data.message,
      messageHistory,
      aiId: data.aiId,
    };

    console.log('\n🤖 ═══ ОТПРАВКА В AI СЕРВИС ═══');
    console.log('Очередь: ai_requests');
    console.log('Chat ID:', chatId);
    console.log('Текущее сообщение:', data.message);
    console.log('История сообщений:', messageHistory.length, 'шт.');
    console.log('AI Model ID:', data.aiId || 'default');
    console.log('Полные данные:', JSON.stringify(aiRequest, null, 2));
    await this.rabbitMQService.sendToAI(aiRequest);
    console.log('✅ Запрос отправлен в AI сервис\n');

    return { status: 'ok', message: 'Сообщение отправлено' };
  }

}
