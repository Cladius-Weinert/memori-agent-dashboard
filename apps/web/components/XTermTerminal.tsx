"use client";
import { useEffect, useRef, useCallback } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

interface XTermTerminalProps {
  wsUrl: string;
  className?: string;
}

export default function XTermTerminal({ wsUrl: url, className = "" }: XTermTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const term = termRef.current;
    if (!term) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      term.write("\r\n\x1b[33m● Connected\x1b[0m\r\n");
      if (fitRef.current) {
        const dims = fitRef.current.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "stdout") {
          term.write(msg.data);
        } else if (msg.type === "exit") {
          term.write(`\r\n\x1b[33m● Session ended (code: ${msg.code})\x1b[0m\r\n`);
          if (msg.error) term.write(`\x1b[31m  ${msg.error}\x1b[0m\r\n`);
        }
      } catch {
        term.write(event.data);
      }
    };

    ws.onerror = () => {
      term.write("\r\n\x1b[31m● Connection error\x1b[0m\r\n");
    };

    ws.onclose = (ev) => {
      if (ev.code === 4001) {
        term.write("\r\n\x1b[31m● Unauthorized\x1b[0m\r\n");
        return;
      }
      term.write("\r\n\x1b[33m● Disconnected\x1b[0m\r\n");
      reconnectTimer.current = setTimeout(() => {
        term.write("\x1b[36m● Reconnecting...\x1b[0m\r\n");
        connect();
      }, 3000);
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "cmd", data }));
      }
    });
  }, [url]);

  useEffect(() => {
    if (!containerRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: "block",
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace",
      lineHeight: 1.3,
      scrollback: 5000,
      theme: {
        background: "#080b12",
        foreground: "#e6edf3",
        cursor: "#d4a053",
        selectionBackground: "#d4a05330",
        black: "#161b22",
        red: "#f85149",
        green: "#3fb950",
        yellow: "#d29922",
        blue: "#58a6ff",
        magenta: "#bc8cff",
        cyan: "#39d2c0",
        white: "#e6edf3",
        brightBlack: "#484f58",
        brightRed: "#ff7b72",
        brightGreen: "#56d364",
        brightYellow: "#e3b341",
        brightBlue: "#79c0ff",
        brightMagenta: "#d2a8ff",
        brightCyan: "#56d4dd",
        brightWhite: "#f0f6fc",
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();
    term.focus();

    termRef.current = term;
    fitRef.current = fitAddon;
    connect();

    const onResize = () => {
      fitAddon.fit();
      const dims = fitAddon.proposeDimensions();
      if (dims && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
      }
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      term.dispose();
    };
  }, [connect]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        minHeight: "300px",
        width: "100%",
        borderRadius: "var(--r-md)",
        overflow: "hidden",
        border: "1px solid var(--b1)",
      }}
    />
  );
}
