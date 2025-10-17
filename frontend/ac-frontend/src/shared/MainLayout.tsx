import type {NavigationItem} from "./types/navigation.ts";
import Sidebar from "./components/Sidebar.tsx";
import {Outlet} from "react-router-dom";

interface SidebarProps {
    routes: NavigationItem[];
}

function MainLayout({ routes } : SidebarProps) {
    return (
        <div>
            <Sidebar routes={routes} />
            <Outlet />
        </div>
    )
}

export default MainLayout