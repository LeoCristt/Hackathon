import { NavLink, Outlet } from "react-router-dom";
import { testChats } from "./ChatView.tsx";

export default function Consultant() {
    const linkClass = ({ isActive }: { isActive: boolean }) =>
        `block p-4 hover:bg-background transition-colors duration-300 rounded-xl cursor-pointer mb-2 ${
            isActive ? "bg-background" : ""
        }`;

    return (
        <div className="flex flex-row h-screen bg-background text-black">
            {/* Список чатов */}
            <div className="w-80 min-w-80 max-w-96 bg-sidebarBackground flex flex-col border-r">
                <div className="p-6 border-b">
                    <h2 className="text-xl font-semibold">Чаты</h2>
                </div>

                <div className="overflow-y-auto flex-1 p-2">
                    {testChats.map(chat => (
                        <NavLink
                            key={chat.id}
                            to={`/consultant/chat/${chat.id}`}
                            className={linkClass}
                        >
                            <div className="font-semibold truncate">{chat.userName}</div>
                            <div className="text-sm text-gray-600 truncate">
                                {chat.lastMessage}
                            </div>
                        </NavLink>
                    ))}
                </div>
            </div>

            {/* Outlet для отображения выбранного чата */}
            <div className="flex-1 min-w-0">
                <Outlet />
            </div>
        </div>
    );
}
