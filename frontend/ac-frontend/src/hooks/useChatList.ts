import { useEffect, useState } from 'react';

export interface ChatSummary {
    chatID: string;
    lastMessage: string;
    updatedAt: string;
}

export function useChatList() {
    const [chats, setChats] = useState<ChatSummary[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchChats();
    }, []);

    const fetchChats = async () => {
        try {
            setIsLoading(true);
            setError(null);

            const token = localStorage.getItem('access_token');

            // Запрос через Kong Gateway с токеном
            const response = await fetch('http://localhost:8000/api/chats/info', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('📊 Получены чаты:', data);

            // Преобразуем данные если нужно
            setChats(data || []);
        } catch (err) {
            console.error('❌ Ошибка загрузки чатов:', err);
            setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
        } finally {
            setIsLoading(false);
        }
    };

    const refreshChats = () => {
        fetchChats();
    };

    return {
        chats,
        isLoading,
        error,
        refreshChats,
    };
}
