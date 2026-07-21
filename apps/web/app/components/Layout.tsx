/* Responsive layout — sidebar desktop, bottom nav mobile */
"use client";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/app/stores/authStore";
import BottomNav from "@/app/components/BottomNav";
import {
  LayoutDashboard,
  Server,
  Terminal,
  Zap,
  Bot,
  Settings,
  LogOut,
  Menu,
  ChevronLeft,
} from "lucide-react";
import { useState } from "react";

const NAV = [
  { href: "/ai", label: "AI Agent", icon: Bot },
  { href: "/dashboard", label: "Activity", icon: LayoutDashboard },
  { href: "/instances", label: "Instances", icon: Server },
  { href: "/commands", label: "Commands", icon: Zap },
  { href: "/settings", label: "Settings", icon: Settings },
];

function Sidebar({ collapsed, setCollapsed }: { collapsed: boolean; setCollapsed: (v: boolean) => void }) {
  const router = useRouter();
  const { logout } = useAuthStore();

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        <button onClick={() => setCollapsed(!collapsed)} className="sidebar-toggle" aria-label="Toggle sidebar">
          {collapsed ? <Menu size={18} /> : <ChevronLeft size={18} />}
        </button>
        {!collapsed && <span className="sidebar-logo">MEMORI</span>}
      </div>

      <nav className="sidebar-nav">
        {NAV.map((item) => (
          <button
            key={item.href}
            onClick={() => router.push(item.href)}
            className="sidebar-item"
          >
            <item.icon size={18} />
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button onClick={logout} className="sidebar-item text-red-400 hover:bg-red-900/20">
          <LogOut size={18} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
      <main className="main-content">{children}</main>
      <BottomNav />
    </div>
  );
}