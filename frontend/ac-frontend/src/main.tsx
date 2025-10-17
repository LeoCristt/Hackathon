import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {createBrowserRouter, RouterProvider} from "react-router-dom";
import './index.css'
import MainLayout from "./shared/MainLayout.tsx";

const router = createBrowserRouter([
    {
        path: "/admin",
        element: <MainLayout />,
        children: []
    },
    {
        path: "/consultant",
        element: <MainLayout />,
        children: []
    }
]);

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <RouterProvider router={router} />
    </StrictMode>,
)
