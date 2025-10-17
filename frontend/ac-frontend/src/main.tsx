import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {createBrowserRouter, RouterProvider} from "react-router-dom";
import './index.css'
import MainLayout from "./shared/MainLayout.tsx";
import type {NavigationItem} from "./shared/types/navigation.ts";

const consultantRoutes : NavigationItem[] = [{path: "/test", label: "Test Path"}];

const router = createBrowserRouter([
    {
        path: "/admin",
        element: <MainLayout />,
        children: []
    },
    {
        path: "/consultant",
        element: <MainLayout routes={consultantRoutes} />,
        children: []
    }
]);

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <RouterProvider router={router} />
    </StrictMode>,
)
