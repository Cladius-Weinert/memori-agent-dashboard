"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  LayoutDashboard,
  Server,
  Zap,
  Settings,
} from "lucide-react";

const TABS = [
  { href: "/ai", label: "AI", icon: Bot },
  { href: "/dashboard", label: "Activity", icon: LayoutDashboard },
  { href: "/instances", label: "Instances", icon: Server },
  { href: "/commands", label: "Commands", icon: Zap },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        const Icon = tab.icon;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`bottom-nav-item${active ? " active" : ""}`}
            aria-label={tab.label}
          >
            <Icon size={18} strokeWidth={active ? 2 : 1.5} />
            <span>{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
