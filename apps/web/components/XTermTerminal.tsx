/* XTerm.js terminal component for WebSocket SSH */
"use client";
import { useEffect, useRef } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";

interface XTermTerminalProps {
  wsUrl: string;
  className?: string;
}

export default function XTermTerminal({ wsUrl: url, className = "h-96" }: XTermTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: "block",
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      theme: {
        background: "#0f172a",
        foreground: "#e2e8f0",
        cursor: "#6366f1",
        black: "#1e293b",
        red: "#ef4444",
        green: "#22c55e",
        yellow: "#eab308",
        blue: "#3b82f6",
        magenta: "#a855f7",
        cyan: "#06b6d4",
        white: "#f8fafc",
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(containerRef.current);
    fitAddon.fit();
    term.focus();

    // WebSocket connection
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      term.write("\r\n\x1b[32mConnected to instance\x1b[0m\r\n");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "stdout") {
          term.write(msg.data);
        } else if (msg.type === "exit") {
          term.write(`\r\n\x1b[33mSession ended (exit code: ${msg.code})\x1b[0m\r\n`);
        }
      } catch {
        // plain text fallback
        term.write(event.data);
      }
    };

    ws.onerror = () => {
      term.write("\r\n\x1b[31mWebSocket error\x1b[0m\r\n");
    };

    ws.onclose = () => {
      term.write("\r\n\x1b[33mDisconnected\x1b[0m\r\n");
    };

    // Handle terminal input → WebSocket
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "cmd", data }));
      }
    });

    // Handle resize
    const onResize = () => fitAddon.fit();
    window.addEventListener("resize", onResize);

    termRef.current = term;

    return () => {
      window.removeEventListener("resize", onResize);
      ws.close();
      term.dispose();
    };
  }, [url]);

  return <div ref={containerRef} className={className} />;
}