"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  LayoutDashboard,
  Server,
  Zap,
  Settings,
  LogOut,
  Box,
  Layers,
} from "lucide-react";
import { useAuthStore } from "@/app/stores/authStore";
import BottomNav from "./BottomNav";
import CommandPalette from "@/components/CommandPalette";
import { ToastProvider } from "@/components/Toast";

const NAV = [
  { href: "/ide", label: "Opsora Agent", icon: Bot },
  { href: "/dashboard", label: "Activity", icon: LayoutDashboard },
  { href: "/instances", label: "Instances", icon: Server },
  { href: "/commands", label: "Commands", icon: Zap },
  { href: "/catalog", label: "Catalog", icon: Box },
  { href: "/workspace", label: "Workspace", icon: Layers },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <ToastProvider>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-header">
            <span className="sidebar-logo">OPSORA</span>
            <span className="sidebar-version">Agent</span>
          </div>

          <nav className="sidebar-nav">
            {NAV.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-item${active ? " active" : ""}`}
                >
                  <Icon size={15} strokeWidth={1.75} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="sidebar-footer">
            <button onClick={handleLogout} className="sidebar-item sidebar-item--logout">
              <LogOut size={15} strokeWidth={1.75} />
              <span>Logout</span>
            </button>
          </div>
        </aside>

        <main className="main-content">{children}</main>

        <BottomNav />
      </div>

      <CommandPalette />
    </ToastProvider>
  );
}
