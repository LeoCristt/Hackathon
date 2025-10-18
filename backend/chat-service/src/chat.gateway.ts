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

  private async handleAIResponse(response: { chatId: string; answer: string; botUsername: string; isManager?: boolean }) {
    const { chatId, answer, botUsername, isManager } = response;

    console.log('\n🎯 ═══ ПОЛУЧЕН ОТВЕТ ОТ AI СЕРВИСА ═══');
    console.log('Очередь: ai_responses');
    console.log('Chat ID:', chatId);
    console.log('Ответ AI:', answer);
    console.log('Bot Username:', botUsername);
    console.log('isManager:', isManager);
    console.log('Полные данные:', JSON.stringify(response, null, 2));

    // Получаем следующий sequence number из Redis (атомарно)
    const sequence = await this.redisService.getNextSequence(chatId);

    const chatMessage: ChatMessage = {
      sequence,
      username: botUsername || 'AI Ассистент',
      message: answer,
      timestamp: new Date().toISOString(),
      chatId,
    };

    console.log('\n📝 Сформированное сообщение AI:');
    console.log('  Sequence:', sequence);
    console.log('  Username:', botUsername);

    // Кэшируем ответ AI в Redis
    await this.redisService.cacheMessage(chatId, chatMessage);
    console.log('✅ Ответ AI закэширован в Redis');

    // Если AI запросил менеджера, сохраняем флаг в Redis
    if (isManager) {
      await this.redisService.setManagerRequired(chatId, true);
      console.log('🔔 Установлен флаг isManager=true для чата', chatId);
    }

    // Сохраняем ответ AI в БД через RabbitMQ (включая isManager флаг)
    console.log('\n📦 ═══ ОТПРАВКА ОТВЕТА AI В БД ═══');
    console.log('Очередь: db_messages');
    const dbPayload = { ...chatMessage, isManager: isManager || false };
    console.log('Данные:', JSON.stringify(dbPayload, null, 2));
    if (isManager) {
      console.log('🔔 ОТПРАВЛЯЕМ isManager=true в operator-service через очередь db_messages');
    }
    await this.rabbitMQService.sendMessageToDB(dbPayload);
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
    console.log('📋 Headers:', JSON.stringify(client.handshake.headers, null, 2));

    // Читаем AI модель из headers (добавлена Kong plugin request-transformer)
    const aiModel = client.handshake.headers['x-widget-ai-model'] as string;
    const domain = client.handshake.headers['x-widget-domain'] as string;
    const isAuthorized = client.handshake.headers['x-widget-authorized'] as string;

    if (!isAuthorized || isAuthorized !== 'true') {
      console.error(`❌ Клиент не авторизован: ${client.id}`);
      client.disconnect();
      return;
    }

    console.log(`✅ Авторизован: domain=${domain}, ai_model=${aiModel}`);

    // Извлекаем username из токена (если есть)
    let username = null;
    const authHeader = client.handshake.headers['authorization'] as string;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      try {
        const token = authHeader.substring(7);
        // Декодируем JWT без проверки подписи (подпись уже проверена на Gateway)
        const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString());
        username = payload.username;
        console.log(`👤 Username из токена: ${username}`);
      } catch (error) {
        console.error('❌ Ошибка при декодировании токена:', error);
      }
    }

    // Сохраняем AI модель и username в сокете
    (client as any).aiModel = aiModel || 'gpt-4';
    (client as any).domain = domain;
    (client as any).username = username;
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
    // Приоритет: 1) username из токена, 2) username из data, 3) "Пользователь"
    const tokenUsername = (client as any).username;
    const username = tokenUsername || data.username || 'Пользователь';

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

    // Получаем следующий sequence number из Redis
    const sequence = await this.redisService.getNextSequence(chatId);

    const chatMessage: ChatMessage = {
      sequence,
      username,
      message: data.message,
      timestamp,
      chatId,
    };

    console.log(`💬 #${sequence} Сообщение от ${username} в чате ${chatId}: ${data.message}`);

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

    // 4. Проверяем, требуется ли менеджер для этого чата
    const isManagerRequired = await this.redisService.isManagerRequired(chatId);

    // 5. Получаем историю сообщений из Redis
    const messageHistory = await this.redisService.getMessageHistory(chatId);

    // 6. Если менеджер не требуется, отправляем запрос в AI
    if (!isManagerRequired) {
      // Получаем AI модель из сокета (установлена Kong plugin)
      const aiModel = (client as any).aiModel || data.aiId || 'gpt-4';
      const domain = (client as any).domain;

      // Отправляем на AI-сервис: сообщение + история + chatId + aiModel
      const aiRequest = {
        chatId,
        message: data.message,
        messageHistory,
        aiId: aiModel, // AI модель из Kong plugin
      };

      console.log('\n🤖 ═══ ОТПРАВКА В AI СЕРВИС ═══');
      console.log('Очередь: ai_requests');
      console.log('Chat ID:', chatId);
      console.log('Domain:', domain);
      console.log('Текущее сообщение:', data.message);
      console.log('История сообщений:', messageHistory.length, 'шт.');
      console.log('AI Model (из Kong):', aiModel);
      console.log('Полные данные:', JSON.stringify(aiRequest, null, 2));
      await this.rabbitMQService.sendToAI(aiRequest);
      console.log('✅ Запрос отправлен в AI сервис\n');
    } else {
      console.log('\n⚠️ Чат в режиме ожидания менеджера - AI запрос не отправлен');
    }

    return { status: 'ok', message: 'Сообщение отправлено' };
  }

}
