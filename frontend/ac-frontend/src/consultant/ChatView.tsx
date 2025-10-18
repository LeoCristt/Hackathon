import { useParams } from "react-router-dom";
import { useChat } from "../hooks/useChat";
import { useState, useEffect, useRef } from "react";

export default function ChatView() {
    const { chatId } = useParams<{ chatId: string }>();
    const { messages, isConnected, sendMessage } = useChat(chatId || null);
    const [inputMessage, setInputMessage] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Автоскролл при новых сообщениях
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    if (!chatId) {
        return (
            <div className="flex-1 flex items-center justify-center bg-background">
                <p className="text-gray-500">Выберите чат для начала общения</p>
            </div>
        );
    }

    const handleSendMessage = () => {
        if (inputMessage.trim() && isConnected) {
            sendMessage(inputMessage);
            setInputMessage('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className="flex flex-col h-full bg-sidebarBackground">
            <div className="p-4 pb-0">
                <h2 className="text-3xl font-semibold truncate">Чат {chatId}</h2>
            </div>

            <div className="flex flex-row justify-center px-2 mt-2">
                <div
                    className="h-1.5 w-full self-center rounded-full bg-white/50 border-2 border-white drop-shadow-lg"></div>
            </div>

            <div className="flex-1 p-6 overflow-y-auto flex flex-col space-y-4">
                {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-500">
                        {isConnected ? 'Загрузка сообщений...' : 'Подключение...'}
                    </div>
                ) : (
                    messages.map((msg, index) => {
                        const isFromUser = msg.username === 'Пользователь';
                        // AI сообщения - любое username, начинающееся с 'AI' или содержащее 'помощник'
                        const isFromAI = msg.username.startsWith('AI') || msg.username.includes('помощник');
                        // Сообщения оператора - username начинается с 'Оператор'
                        const isFromOperator = msg.username.startsWith('Оператор');

                        return (
                            <div
                                key={`${msg.sequence}-${index}`}
                                className={`${
                                    isFromUser
                                        ? 'self-end bg-accentColor/35 border-2 border-accentColor drop-shadow-lg rounded-[12px_12px_0_12px]'
                                        : isFromAI
                                        ? 'self-start bg-blue-500/35 border-2 border-blue-500 drop-shadow-lg rounded-[12px_12px_12px_0]'
                                        : isFromOperator
                                        ? 'self-start bg-green-500/35 border-2 border-green-500 drop-shadow-lg rounded-[12px_12px_12px_0]'
                                        : 'self-start bg-accentColorLightOpposite/35 border-2 border-accentColorLightOpposite drop-shadow-lg rounded-[12px_12px_12px_0]'
                                }  px-4 py-3 text-black max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg xl:max-w-xl`}
                                style={{ wordBreak: 'break-word' }}
                            >
                                <div className="font-semibold text-sm mb-1">{msg.username}</div>
                                <div>{msg.message}</div>
                            </div>
                        );
                    })
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="flex flex-row justify-center px-2 mb-2">
                <div
                    className="h-1.5 w-full self-center rounded-full bg-white/50 border-2 border-white drop-shadow-lg"></div>
            </div>


            <div className="p-2 pb-4  bg-sidebarBackground flex items-center gap-3">
                <label className="flex-1">
                    <input
                        type="text"
                        placeholder="Введите сообщение..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={!isConnected}
                        className="w-full hover:bg-sidebarBackground bg-sidebarBackground/50 border-2 border-sidebarBackground drop-shadow-lg rounded-xl px-4 py-3 focus:outline-none transition-colors duration-300"
                    />
                </label>
                <button
                    onClick={handleSendMessage}
                    disabled={!isConnected || !inputMessage.trim()}
                    className="px-6 py-3 rounded-xl hover:bg-accentColor bg-accentColor/35 border-2 border-accentColor drop-shadow-lg duration-300 font-medium whitespace-nowrap">
                    Отправить
                </button>
            </div>
        </div>
    );
}
