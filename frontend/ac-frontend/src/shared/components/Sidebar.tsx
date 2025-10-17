import type {NavigationItem} from '../types/navigation.ts';
import {Link} from "react-router-dom";

interface SidebarProps {
    routes: NavigationItem[];
}

function Sidebar({ routes } : SidebarProps) {
    return (
        <>
            {routes.map(route => (
                <Link to={route.path}>{route.label}</Link>
            ))}
        </>
    )
}

export default Sidebar;