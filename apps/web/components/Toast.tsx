"use client";
import {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
} from "react";
import { CheckCircle, XCircle, AlertTriangle, Info, X } from "lucide-react";

/* ── types ── */
type ToastType = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastCtx {
  toast: (message: string, type?: ToastType) => void;
}

/* ── context ── */
const Ctx = createContext<ToastCtx>({ toast: () => {} });

export function useToast() {
  return useContext(Ctx);
}

/* ── style map ── */
const ICON: Record<ToastType, React.ElementType> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const COLOR: Record<ToastType, string> = {
  success: "var(--ok, #4ade80)",
  error: "var(--err, #f87171)",
  warning: "var(--warn, #fbbf24)",
  info: "var(--info, #60a5fa)",
};

/* ── provider ── */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  let nextId = 0;

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => {
      const next = [...prev, { id, message, type }];
      // keep at most 3
      return next.length > 3 ? next.slice(-3) : next;
    });
    // auto-dismiss after 4 s
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <Ctx.Provider value={{ toast }}>
      {children}

      {/* toast stack — bottom-right desktop, top-center mobile */}
      <div
        style={{
          position: "fixed",
          zIndex: 10000,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          pointerEvents: "none",
          /* bottom-right by default */
          bottom: 20,
          right: 20,
        }}
        className="toast-stack"
      >
        <style>{`
          @keyframes toastIn {
            from { opacity: 0; transform: translateX(24px); }
            to   { opacity: 1; transform: translateX(0); }
          }
          @media (max-width: 640px) {
            .toast-stack {
              bottom: auto !important;
              right: auto !important;
              top: 16px !important;
              left: 50% !important;
              transform: translateX(-50%) !important;
              align-items: center !important;
            }
          }
        `}</style>
        {toasts.map((t) => {
          const Icon = ICON[t.type];
          return (
            <div
              key={t.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                background: "var(--s2)",
                border: `1px solid ${COLOR[t.type]}`,
                borderRadius: "var(--r-md)",
                boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
                minWidth: 240,
                maxWidth: 380,
                pointerEvents: "auto",
                animation: "toastIn 0.2s ease-out",
              }}
            >
              <Icon size={16} style={{ color: COLOR[t.type], flexShrink: 0 }} />
              <span
                style={{
                  flex: 1,
                  fontFamily: "var(--sans)",
                  fontSize: 13,
                  color: "var(--t1)",
                  lineHeight: 1.4,
                }}
              >
                {t.message}
              </span>
              <button
                onClick={() => dismiss(t.id)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--t3)",
                  padding: 2,
                  flexShrink: 0,
                }}
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
}
