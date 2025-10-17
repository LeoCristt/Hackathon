import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {createBrowserRouter, RouterProvider} from "react-router-dom";
import './index.css'
import MainLayout from "./shared/MainLayout.tsx";
import type {NavigationItem} from "./shared/types/navigation.ts";
import Consultant from "./consultant/Consultant.tsx";
import ChatView from "./consultant/ChatView.tsx";
import ChatPlaceholder from "./consultant/ChatPlaceholder.tsx";

const consultantRoutes : NavigationItem[] = [{path: "", label: "Чаты"}, {path: "/stats", label: "Статистика"}];

const router = createBrowserRouter([
    {
        path: "/admin",
        element: <MainLayout />,
        children: []
    },
    {
        path: "/consultant",
        element: <MainLayout routes={consultantRoutes} />,
        children: [
            {
                path: "",
                element: <Consultant />,
                children: [
                    {
                        path: "",
                        element: <ChatPlaceholder />
                    },
                    {
                        path: "chat/:chatId",
                        element: <ChatView />
                    }
                ]
            }
        ]
    }
]);

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <RouterProvider router={router} />
    </StrictMode>,
)
