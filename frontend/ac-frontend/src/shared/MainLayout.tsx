import type {NavigationItem} from "./types/navigation.ts";
import Sidebar from "./components/Sidebar.tsx";

interface SidebarProps {
    routes: NavigationItem[];
}

function MainLayout({ routes } : SidebarProps) {
    return (
        <>
            <Sidebar routes={routes} />
        </>
    )
}

export default MainLayout