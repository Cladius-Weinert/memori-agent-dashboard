"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Bot,
  Server,
  Terminal,
  Settings,
  Zap,
  Download,
  Brain,
  ArrowRight,
} from "lucide-react";

interface Command {
  label: string;
  icon: React.ElementType;
  action: () => void;
}

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const commands: Command[] = [
    { label: "Go to AI Agent", icon: Bot, action: () => router.push("/ai") },
    { label: "Go to Dashboard", icon: Server, action: () => router.push("/dashboard") },
    { label: "Go to Instances", icon: Server, action: () => router.push("/instances") },
    { label: "Go to Commands", icon: Terminal, action: () => router.push("/commands") },
    { label: "Go to Settings", icon: Settings, action: () => router.push("/settings") },
    { label: "New Chat", icon: Bot, action: () => router.push("/ai?new=1") },
    {
      label: "Export Data",
      icon: Download,
      action: () => {
        const blob = new Blob([JSON.stringify({ exported: true }, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "opsora-export.json";
        a.click();
        URL.revokeObjectURL(url);
      },
    },
    {
      label: "Toggle Memory Panel",
      icon: Brain,
      action: () => window.dispatchEvent(new CustomEvent("toggle-memory-panel")),
    },
  ];

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  const execute = useCallback(
    (cmd: Command) => {
      setOpen(false);
      setQuery("");
      setActive(0);
      cmd.action();
    },
    []
  );

  /* keyboard shortcut to open */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        setQuery("");
        setActive(0);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  /* auto-focus input when opened */
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  /* reset active index when filter changes */
  useEffect(() => {
    setActive(0);
  }, [query]);

  if (!open) return null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && filtered[active]) {
      e.preventDefault();
      execute(filtered[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
      setQuery("");
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "18vh",
        background: "rgba(0,0,0,0.55)",
        backdropFilter: "blur(6px)",
        animation: "cmdFadeIn 0.15s ease-out",
      }}
      onClick={() => {
        setOpen(false);
        setQuery("");
      }}
    >
      <style>{`
        @keyframes cmdFadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes cmdSlideUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 520,
          background: "var(--s2)",
          border: "1px solid var(--b1)",
          borderRadius: "var(--r-md)",
          boxShadow: "0 24px 48px rgba(0,0,0,0.4)",
          animation: "cmdSlideUp 0.18s ease-out",
          overflow: "hidden",
        }}
      >
        {/* search input */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "12px 16px",
            borderBottom: "1px solid var(--b1)",
          }}
        >
          <Search size={16} style={{ color: "var(--t3)", flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command…"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--t1)",
              fontFamily: "var(--mono)",
              fontSize: 14,
            }}
          />
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              color: "var(--t3)",
              background: "var(--s3)",
              padding: "2px 6px",
              borderRadius: "var(--r-sm)",
              border: "1px solid var(--b1)",
            }}
          >
            ESC
          </span>
        </div>

        {/* command list */}
        <div style={{ maxHeight: 320, overflowY: "auto", padding: "6px 0" }}>
          {filtered.length === 0 && (
            <div
              style={{
                padding: "20px 16px",
                textAlign: "center",
                color: "var(--t3)",
                fontFamily: "var(--mono)",
                fontSize: 12,
              }}
            >
              No matching commands
            </div>
          )}
          {filtered.map((cmd, i) => {
            const Icon = cmd.icon;
            const isActive = i === active;
            return (
              <button
                key={cmd.label}
                onClick={() => execute(cmd)}
                onMouseEnter={() => setActive(i)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  width: "100%",
                  padding: "10px 16px",
                  background: isActive ? "var(--s3)" : "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: isActive ? "var(--accent)" : "var(--t1)",
                  fontFamily: "var(--sans)",
                  fontSize: 13,
                  textAlign: "left",
                  transition: "background 0.1s",
                }}
              >
                <Icon size={15} strokeWidth={1.75} />
                <span style={{ flex: 1 }}>{cmd.label}</span>
                {isActive && <ArrowRight size={13} style={{ color: "var(--accent)" }} />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
