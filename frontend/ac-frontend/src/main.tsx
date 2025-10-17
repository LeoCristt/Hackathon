import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {createBrowserRouter, RouterProvider} from "react-router-dom";
import './index.css'
import MainLayout from "./shared/MainLayout.tsx";
import type {NavigationItem} from "./shared/types/navigation.ts";
import Consultant from "./consultant/Consultant.tsx";
import ChatView from "./consultant/ChatView.tsx";
import ChatPlaceholder from "./consultant/ChatPlaceholder.tsx";
import LoginPage from "./auth/LoginPage.tsx";
import ProtectedRoute from "./auth/ProtectedRoute.tsx";
import { AuthProvider } from "./auth/AuthContext.tsx";

const consultantRoutes : NavigationItem[] = [{path: "", label: "Чаты"}, {path: "/stats", label: "Статистика"}];
const adminRoutes : NavigationItem[] = [{path: "/admin", label: "Админ панель"}];

const router = createBrowserRouter([
    {
        path: "/login",
        element: <LoginPage />
    },
    {
        path: "/admin",
        element: (
            <ProtectedRoute>
                <MainLayout routes={adminRoutes} />
            </ProtectedRoute>
        ),
        children: []
    },
    {
        path: "/",
        element: (
            <ProtectedRoute>
                <MainLayout routes={consultantRoutes} />
            </ProtectedRoute>
        ),
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
        <AuthProvider>
            <RouterProvider router={router} />
        </AuthProvider>
    </StrictMode>,
)
