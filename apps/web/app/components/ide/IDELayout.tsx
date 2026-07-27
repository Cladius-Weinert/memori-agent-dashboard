"use client";

import Link from "next/link";
import { Files, MessageSquare, Server, Settings, Layers, GitBranch } from "lucide-react";
import { FileTree } from "./FileTree";
import { GitPanel } from "./GitPanel";
import { CodeEditor } from "./CodeEditor";
import { AgentPanel } from "./AgentPanel";
import { BottomPanel } from "./BottomPanel";
import { useIDEStore } from "@/app/stores/ideStore";

export function IDELayout() {
  const sidebarTab = useIDEStore((s) => s.sidebarTab);
  const setSidebarTab = useIDEStore((s) => s.setSidebarTab);

  return (
    <div className="ide-shell">
      <aside className="ide-activity-bar">
        <Link href="/ide" className="ide-logo" title="Opsora Agent">
          OA
        </Link>
        <button
          type="button"
          className={sidebarTab === "files" ? "active" : ""}
          onClick={() => setSidebarTab("files")}
          title="Files"
        >
          <Files size={18} />
        </button>
        <button
          type="button"
          className={sidebarTab === "git" ? "active" : ""}
          onClick={() => setSidebarTab("git")}
          title="Git"
        >
          <GitBranch size={18} />
        </button>
        <button
          type="button"
          className={sidebarTab === "chats" ? "active" : ""}
          onClick={() => setSidebarTab("chats")}
          title="Chats"
        >
          <MessageSquare size={18} />
        </button>
        <div className="flex-1" />
        <Link href="/instances" className="ide-activity-link" title="Instances">
          <Server size={18} />
        </Link>
        <Link href="/workspace" className="ide-activity-link" title="Workspace">
          <Layers size={18} />
        </Link>
        <Link href="/settings" className="ide-activity-link" title="Settings">
          <Settings size={18} />
        </Link>
      </aside>

      <aside className="ide-sidebar">
        <div className="ide-sidebar-title">
          {sidebarTab === "files" ? "EXPLORER" : sidebarTab === "git" ? "SOURCE CONTROL" : "CHAT"}
        </div>
        {sidebarTab === "files" && <FileTree />}
        {sidebarTab === "git" && <GitPanel />}
        {sidebarTab === "chats" && (
          <div className="p-3 text-xs" style={{ color: "var(--t3)" }}>
            Gunakan panel agent di kanan untuk chat. Riwayat tersimpan otomatis.
          </div>
        )}
      </aside>

      <main className="ide-main">
        <div className="ide-workspace">
          <div className="ide-center">
            <CodeEditor />
          </div>
          <div className="ide-right">
            <AgentPanel />
          </div>
        </div>
        <BottomPanel />
      </main>
    </div>
  );
}
