import { create } from "zustand";

interface Toast {
  id: string;
  message: string;
  type: "ok" | "err" | "warn" | "info";
}

interface UIState {
  toasts: Toast[];
  cmdOpen: boolean;
  addToast: (message: string, type?: Toast["type"]) => void;
  removeToast: (id: string) => void;
  setCmdOpen: (open: boolean) => void;
}

let toastId = 0;

export const useUIStore = create<UIState>((set, get) => ({
  toasts: [],
  cmdOpen: false,

  addToast: (message, type = "info") => {
    const id = `t-${++toastId}`;
    set((s) => ({ toasts: [...s.toasts.slice(-2), { id, message, type }] }));
    setTimeout(() => get().removeToast(id), 4000);
  },

  removeToast: (id) => {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
  },

  setCmdOpen: (open) => set({ cmdOpen: open }),
}));
