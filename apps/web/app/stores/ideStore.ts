import { create } from "zustand";
import type { DiffLine } from "@/app/components/ide/DiffViewer";

export type OpenFile = {
  path: string;
  content: string;
  dirty: boolean;
};

type IDEState = {
  openFiles: OpenFile[];
  activePath: string | null;
  sidebarTab: "files" | "git" | "chats";
  bottomTab: "terminal" | "output";
  terminalInstanceId: number | null;
  setActivePath: (path: string | null) => void;
  openFile: (path: string, content: string) => void;
  updateContent: (path: string, content: string) => void;
  markSaved: (path: string) => void;
  closeFile: (path: string) => void;
  setSidebarTab: (tab: "files" | "git" | "chats") => void;
  setBottomTab: (tab: "terminal" | "output") => void;
  setTerminalInstanceId: (id: number | null) => void;
};

export const useIDEStore = create<IDEState>((set, get) => ({
  openFiles: [],
  activePath: null,
  sidebarTab: "files",
  bottomTab: "terminal",
  terminalInstanceId: null,
  setActivePath: (path) => set({ activePath: path }),
  openFile: (path, content) => {
    const existing = get().openFiles.find((f) => f.path === path);
    if (existing) {
      set({ activePath: path });
      return;
    }
    set({
      openFiles: [...get().openFiles, { path, content, dirty: false }],
      activePath: path,
    });
  },
  updateContent: (path, content) => {
    set({
      openFiles: get().openFiles.map((f) =>
        f.path === path ? { ...f, content, dirty: true } : f,
      ),
    });
  },
  markSaved: (path) => {
    set({
      openFiles: get().openFiles.map((f) =>
        f.path === path ? { ...f, dirty: false } : f,
      ),
    });
  },
  closeFile: (path) => {
    const remaining = get().openFiles.filter((f) => f.path !== path);
    const activePath = get().activePath === path ? remaining[0]?.path ?? null : get().activePath;
    set({ openFiles: remaining, activePath });
  },
  setSidebarTab: (tab) => set({ sidebarTab: tab }),
  setBottomTab: (tab) => set({ bottomTab: tab }),
  setTerminalInstanceId: (id) => set({ terminalInstanceId: id }),
}));
