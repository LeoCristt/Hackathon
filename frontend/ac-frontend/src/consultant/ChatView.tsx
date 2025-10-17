import { useParams } from "react-router-dom";

interface Message {
    id: number;
    text: string;
    isFromUser: boolean;
    timestamp: string;
}

interface Chat {
    id: number;
    userName: string;
    lastMessage: string;
    timestamp: string;
    messages: Message[];
}

const testChats: Chat[] = [
    {
        id: 1,
        userName: "Иван Иванов",
        lastMessage: "Спасибо за помощь!",
        timestamp: "10:23",
        messages: [
            { id: 1, text: "Здравствуйте! Чем могу помочь?", isFromUser: false, timestamp: "10:20" },
            { id: 2, text: "У меня не работает сайт", isFromUser: true, timestamp: "10:21" },
            { id: 3, text: "Уточните, пожалуйста, какая страница не загружается?", isFromUser: false, timestamp: "10:22" },
            { id: 4, text: "Спасибо за помощь! Очень длинное сообщение с множеством слов и superlongwordthatshouldbreaknormally", isFromUser: true, timestamp: "10:23" }
        ]
    },
    {
        id: 2,
        userName: "Анна Петрова",
        lastMessage: "Когда доставка?",
        timestamp: "09:58",
        messages: [
            { id: 1, text: "Добро пожаловать! Как дела?", isFromUser: false, timestamp: "09:55" },
            { id: 2, text: "Когда доставка? Мне нужно знать точное время", isFromUser: true, timestamp: "09:58" }
        ]
    },
    {
        id: 3,
        userName: "Сергей Смирнов",
        lastMessage: "Не могу войти в аккаунт",
        timestamp: "09:30",
        messages: [
            { id: 1, text: "Здравствуйте! Чем могу помочь?", isFromUser: false, timestamp: "09:28" },
            { id: 2, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 3, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 4, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 5, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 6, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 7, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 8, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 9, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 10, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 11, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 12, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 13, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
            { id: 14, text: "Не могу войти в аккаунт, пароль не подходит", isFromUser: true, timestamp: "09:30" },
        ]
    }
];

export default function ChatView() {
    const { chatId } = useParams();
    const chat = testChats.find(c => c.id === Number(chatId));

    if (!chat) {
        return (
            <div className="flex-1 flex items-center justify-center bg-background">
                <p className="text-gray-500">Выберите чат для начала общения</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-sidebarBackground">
            <div className="p-4 pb-0">
                <h2 className="text-3xl font-semibold truncate">Чат с {chat.userName}</h2>
            </div>

            <div className="flex flex-row justify-center px-2 mt-2">
                <div
                    className="h-1.5 w-full self-center rounded-full bg-white/50 border-2 border-white drop-shadow-lg"></div>
            </div>

            <div className="flex-1 p-6 overflow-y-auto flex flex-col space-y-4">
                {chat.messages.map(message => (
                    <div
                        key={message.id}
                        className={`${
                            message.isFromUser ? 'self-end bg-accentColor/35 border-2 border-accentColor drop-shadow-lg rounded-[12px_12px_0_12px]' : 'self-start bg-accentColorLightOpposite/35 border-2 border-accentColorLightOpposite drop-shadow-lg rounded-[12px_12px_12px_0]'
                        }  px-4 py-3 text-black max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg xl:max-w-xl`}
                        style={{ wordBreak: 'break-word' }}
                    >
                        {message.text}
                    </div>
                ))}
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
                        className="w-full hover:bg-sidebarBackground bg-sidebarBackground/50 border-2 border-sidebarBackground drop-shadow-lg rounded-xl px-4 py-3 focus:outline-none transition-colors duration-300"
                    />
                </label>
                <button className="px-6 py-3 rounded-xl hover:bg-accentColor bg-accentColor/35 border-2 border-accentColor drop-shadow-lg duration-300 font-medium whitespace-nowrap">
                    Отправить
                </button>
            </div>
        </div>
    );
}

export { testChats };
