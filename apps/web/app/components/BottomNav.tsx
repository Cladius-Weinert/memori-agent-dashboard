/* Mobile bottom tab navigation — native feel */
"use client";
import { useRouter, usePathname } from "next/navigation";
import {
  Bot,
  Server,
  TerminalSquare,
  Activity,
  Settings,
} from "lucide-react";

const TABS = [
  { href: "/ai", label: "AI", icon: Bot },
  { href: "/instances", label: "Instances", icon: Server },
  { href: "/commands", label: "Commands", icon: TerminalSquare },
  { href: "/dashboard", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function BottomNav() {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => {
        const active = pathname.startsWith(tab.href);
        return (
          <button
            key={tab.href}
            onClick={() => router.push(tab.href)}
            className={`bottom-nav-item ${active ? "active" : ""}`}
            aria-label={tab.label}
          >
            <tab.icon size={20} strokeWidth={active ? 2.5 : 1.5} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}