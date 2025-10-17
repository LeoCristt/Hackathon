import type {NavigationItem} from "./types/navigation.ts";
import Sidebar from "./components/Sidebar.tsx";
import {Outlet} from "react-router-dom";

interface SidebarProps {
    routes: NavigationItem[];
}

function MainLayout({routes}: SidebarProps) {
    return (
        <div className="w-screen flex flex-row">
            <Sidebar routes={routes}/>
            <main className="overflow-y-auto">
                <Outlet/>
            </main>
        </div>
    )
}

export default MainLayout