import { NavLink, Outlet } from "react-router-dom";
import { testChats } from "./ChatView.tsx";

export default function Consultant() {
    const linkClass = ({isActive}: { isActive: boolean }) =>
        `transition-colors duration-300 rounded-xl p-3 ${
            isActive
                ? "hover:bg-accentColor bg-accentColor/35 border-2 border-accentColor drop-shadow-lg"
                : "hover:bg-sidebarBackground bg-sidebarBackground/35 border-2 border-sidebarBackground/50 drop-shadow-lg"
        }`;

    return (
        <div className="flex flex-row h-screen bg-background text-black">
            {/* Список чатов */}
            <div className="w-80 min-w-80 max-w-96 bg-sidebarBackground flex flex-col">
                <div className="p-4 pb-0">
                    <h2 className="text-3xl font-semibold">Чаты</h2>
                </div>

                <div className="flex flex-row justify-center px-2 my-2">
                    <div
                        className="h-1.5 w-full self-center rounded-full bg-white/50 border-2 border-white drop-shadow-lg"></div>
                </div>

                <div className="overflow-y-auto w-full p-2 flex flex-col gap-4 drop-shadow-2xl h-full">
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
