"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useIDEStore } from "@/app/stores/ideStore";
import { filesApi, gitApi } from "@/app/api/api";
import { DiffViewer, type DiffLine } from "./DiffViewer";

const Monaco = dynamic(() => import("@monaco-editor/react"), { ssr: false });

export function CodeEditor() {
  const openFiles = useIDEStore((s) => s.openFiles);
  const activePath = useIDEStore((s) => s.activePath);
  const updateContent = useIDEStore((s) => s.updateContent);
  const markSaved = useIDEStore((s) => s.markSaved);
  const closeFile = useIDEStore((s) => s.closeFile);
  const setActivePath = useIDEStore((s) => s.setActivePath);
  const setBottomTab = useIDEStore((s) => s.setBottomTab);

  const [pendingSave, setPendingSave] = useState<{
    path: string;
    content: string;
    lines: DiffLine[];
  } | null>(null);

  const active = openFiles.find((f) => f.path === activePath);

  const save = async () => {
    if (!active) return;
    try {
      const diff = await gitApi.textDiff(active.path, active.content);
      if (diff.has_changes && diff.lines?.length) {
        setPendingSave({
          path: active.path,
          content: active.content,
          lines: diff.lines as DiffLine[],
        });
        setBottomTab("output");
        return;
      }
      await filesApi.write(active.path, active.content);
      markSaved(active.path);
    } catch {
      await filesApi.write(active.path, active.content);
      markSaved(active.path);
    }
  };

  const confirmSave = async () => {
    if (!pendingSave) return;
    await filesApi.write(pendingSave.path, pendingSave.content);
    markSaved(pendingSave.path);
    setPendingSave(null);
  };

  return (
    <div className="ide-editor">
      <div className="ide-tabs">
        {openFiles.map((f) => (
          <button
            key={f.path}
            type="button"
            className={`ide-tab${f.path === activePath ? " active" : ""}`}
            onClick={() => setActivePath(f.path)}
          >
            <span>{f.path.split("/").pop()}{f.dirty ? " •" : ""}</span>
            <span
              className="ide-tab-close"
              onClick={(e) => {
                e.stopPropagation();
                closeFile(f.path);
              }}
            >
              ×
            </span>
          </button>
        ))}
        {active && (
          <button type="button" className="ide-save-btn" onClick={save}>
            Save
          </button>
        )}
      </div>
      <div className="ide-editor-body">
        {pendingSave && activePath === pendingSave.path ? (
          <DiffViewer
            path={pendingSave.path}
            lines={pendingSave.lines}
            title="Review changes before save"
            onAccept={confirmSave}
            onReject={() => setPendingSave(null)}
          />
        ) : active ? (
          <Monaco
            height="100%"
            theme="vs-dark"
            language={guessLanguage(active.path)}
            value={active.content}
            onChange={(v) => updateContent(active.path, v ?? "")}
            options={{
              fontSize: 13,
              fontFamily: "JetBrains Mono, monospace",
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        ) : (
          <div className="ide-empty">
            <p>Opsora Agent IDE</p>
            <span>Buka file dari sidebar atau minta agent menganalisis workspace.</span>
          </div>
        )}
      </div>
    </div>
  );
}

function guessLanguage(path: string): string {
  if (path.endsWith(".tsx") || path.endsWith(".ts")) return "typescript";
  if (path.endsWith(".jsx") || path.endsWith(".js")) return "javascript";
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".json")) return "json";
  if (path.endsWith(".md")) return "markdown";
  if (path.endsWith(".css")) return "css";
  if (path.endsWith(".html")) return "html";
  if (path.endsWith(".sh")) return "shell";
  return "plaintext";
}
