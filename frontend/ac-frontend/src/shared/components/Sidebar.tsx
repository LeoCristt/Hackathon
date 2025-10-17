import type {NavigationItem} from '../types/navigation.ts';
import {Link} from "react-router-dom";

interface SidebarProps {
    routes: NavigationItem[];
}

function Sidebar({ routes } : SidebarProps) {
    return (
        <div className="h-screen w-72 bg-red-400">
            <h1><span className="text-accentColor">AI</span> Helper</h1>
            {routes.map(route => (
                <Link to={route.path}>{route.label}</Link>
            ))}
        </div>
    )
}

export default Sidebar;