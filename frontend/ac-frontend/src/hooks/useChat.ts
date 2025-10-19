import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export interface ChatMessage {
    sequence: number;
    username: string;
    message: string;
    timestamp: string;
    chatId: string;
}

export interface Chat {
    id: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    messageCount: number;
}

export function useChat(chatId: string | null) {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const socketRef = useRef<Socket | null>(null);

    useEffect(() => {
        // Если chatId не указан, не подключаемся
        if (!chatId) {
            return;
        }

        console.log('🔌 Подключение к WebSocket для чата:', chatId);

        // Получаем токен из localStorage
        const token = localStorage.getItem('access_token');

        // Создаем новое подключение
        const newSocket = io('http://172.29.67.31:8000', {
            path: '/socket.io',
            transports: ['polling', 'websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5,
            withCredentials: true,
            forceNew: true,
            extraHeaders: token ? {
                'Authorization': `Bearer ${token}`
            } : undefined,
        });

        socketRef.current = newSocket;
        setSocket(newSocket);

        // Обработчик подключения
        newSocket.on('connect', () => {
            console.log('✅ Подключено к WebSocket');
            setIsConnected(true);

            // Отправляем событие join после подключения (username будет извлечен из токена на сервере)
            newSocket.emit('join', {
                chatId: chatId,
            });
        });

        // Обработчик отключения
        newSocket.on('disconnect', () => {
            console.log('❌ Отключено от WebSocket');
            setIsConnected(false);
        });

        // Обработчик получения сообщения
        newSocket.on('message', (data: ChatMessage) => {
            console.log('📨 Получено сообщение:', data);
            setMessages((prev) => [...prev, data]);
        });

        // Обработчик получения истории
        newSocket.on('history', (history: ChatMessage[]) => {
            console.log('📚 Получена история:', history.length, 'сообщений');
            setMessages(history);
        });

        // Cleanup при размонтировании или смене chatId
        return () => {
            console.log('🔌 Отключаемся от WebSocket');
            newSocket.disconnect();
            socketRef.current = null;
        };
    }, [chatId]);

    const sendMessage = (message: string) => {
        if (socket && socket.connected) {
            socket.emit('message', { message });
            console.log('📤 Отправлено сообщение:', message);
        } else {
            console.error('❌ Socket не подключен');
        }
    };

    return {
        messages,
        isConnected,
        sendMessage,
    };
}
