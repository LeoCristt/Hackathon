export default function Consultant() {
    return (
        <div className="w-full flex flex-row h-screen text-black">
            {/* Список чатов */}
            <div className="w-1/4 flex flex-col border-r">
                <div className="p-6 border-b">
                    <h2 className="text-xl font-semibold">Чаты</h2>
                </div>

                <div className="flex-1 p-2 overflow-y-auto">
                    <div className="p-4 hover:bg-background transition-colors duration-300 rounded-xl cursor-pointer mb-2">
                        <div className="font-semibold">Иван Иванов</div>
                        <div className="text-sm text-gray-600 truncate">
                            Спасибо за помощь!
                        </div>
                        <div className="text-xs text-gray-400 mt-1">10:23</div>
                    </div>

                    <div className="p-4 hover:bg-background transition-colors duration-300 rounded-xl cursor-pointer mb-2">
                        <div className="font-semibold">Анна Петрова</div>
                        <div className="text-sm text-gray-600 truncate">
                            Когда доставка?
                        </div>
                        <div className="text-xs text-gray-400 mt-1">09:58</div>
                    </div>

                    <div className="p-4 hover:bg-background transition-colors duration-300 rounded-xl cursor-pointer mb-2">
                        <div className="font-semibold">Сергей Смирнов</div>
                        <div className="text-sm text-gray-600 truncate">
                            Не могу войти в аккаунт
                        </div>
                        <div className="text-xs text-gray-400 mt-1">09:30</div>
                    </div>
                </div>
            </div>

            {/* Окно чата */}
            <div className="flex-3/4 flex flex-col bg-sidebarBackground">
                <div className="p-6 border-b">
                    <h2 className="font-semibold text-xl">Чат с пользователем</h2>
                </div>

                <div className="flex-1 p-6 overflow-y-auto flex flex-col space-y-4">
                    <div className="self-start bg-accentColorLightOpposite rounded-[12px_12px_12px_0] px-4 py-3 max-w-xs shadow-sm">
                        Здравствуйте! Чем могу помочь?
                    </div>
                    <div className="self-end bg-accentColorLight text-black rounded-[12px_12px_0_12px] px-4 py-3 max-w-xs shadow-sm">
                        У меня не работает сайт
                    </div>
                    <div className="self-start bg-accentColorLightOpposite rounded-[12px_12px_12px_0] px-4 py-3 max-w-xs shadow-sm">
                        Уточните, пожалуйста, какая страница не загружается?
                    </div>
                </div>

                <div className="p-6 border-t flex items-center gap-3">
                    <label className="flex-1">
                        <input
                            type="text"
                            placeholder="Введите сообщение..."
                            className="w-full border rounded-xl px-4 py-3 focus:outline-none"
                        />
                    </label>
                    <button className="px-6 py-3 rounded-xl bg-accentColor hover:bg-accentColorLight transition-colors duration-300 font-medium">
                        Отправить
                    </button>
                </div>
            </div>
        </div>
    );
}
