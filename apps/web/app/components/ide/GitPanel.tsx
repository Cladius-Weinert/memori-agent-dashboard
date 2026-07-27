"use client";

import { useCallback, useEffect, useState } from "react";
import { GitBranch, GitCommit, RefreshCw, FileDiff } from "lucide-react";
import { gitApi } from "@/app/api/api";
import { useIDEStore } from "@/app/stores/ideStore";
import { DiffViewer, type DiffLine } from "./DiffViewer";

type GitStatus = {
  branch?: string;
  clean?: boolean;
  staged?: Array<{ path: string; status: string }>;
  unstaged?: Array<{ path: string; status: string }>;
  untracked?: string[];
};

export function GitPanel() {
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [commitMsg, setCommitMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [diffPath, setDiffPath] = useState<string | null>(null);
  const [diffLines, setDiffLines] = useState<DiffLine[]>([]);
  const openFile = useIDEStore((s) => s.openFile);
  const setBottomTab = useIDEStore((s) => s.setBottomTab);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const s = await gitApi.status();
      setStatus(s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const showDiff = async (path: string) => {
    try {
      const d = await gitApi.diff(path);
      const lines: DiffLine[] = [];
      for (const hunk of d.hunks ?? []) {
        for (const line of hunk.lines ?? []) {
          lines.push(line as DiffLine);
        }
      }
      if (!lines.length && d.raw) {
        d.raw.split("\n").forEach((text: string) => {
          if (text.startsWith("+")) lines.push({ type: "add", text: text.slice(1) });
          else if (text.startsWith("-")) lines.push({ type: "del", text: text.slice(1) });
          else lines.push({ type: "ctx", text });
        });
      }
      setDiffPath(path);
      setDiffLines(lines);
      setBottomTab("output");
    } catch (e) {
      console.error(e);
    }
  };

  const stageAll = async () => {
    await gitApi.add([]);
    await refresh();
  };

  const commit = async () => {
    if (!commitMsg.trim()) return;
    await gitApi.commit(commitMsg.trim());
    setCommitMsg("");
    await refresh();
  };

  const openChangedFile = async (path: string) => {
    const { filesApi } = await import("@/app/api/api");
    const data = await filesApi.read(path);
    openFile(path, data.content);
  };

  const changed = [
    ...(status?.staged ?? []).map((f) => ({ ...f, group: "staged" })),
    ...(status?.unstaged ?? []).map((f) => ({ ...f, group: "modified" })),
    ...(status?.untracked ?? []).map((p) => ({ path: p, status: "?", group: "untracked" })),
  ];

  return (
    <div className="ide-git">
      <div className="ide-git-header">
        <GitBranch size={14} />
        <span className="mono">{status?.branch ?? "—"}</span>
        <button type="button" onClick={refresh} title="Refresh" className="ide-git-refresh">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {diffPath && diffLines.length > 0 && (
        <DiffViewer
          path={diffPath}
          lines={diffLines}
          title="Git diff"
          onReject={() => { setDiffPath(null); setDiffLines([]); }}
        />
      )}

      <div className="ide-git-section">
        <div className="ide-git-section-title">CHANGES ({changed.length})</div>
        {changed.length === 0 && (
          <div className="ide-git-empty">{status?.clean ? "Working tree clean" : "No changes"}</div>
        )}
        {changed.map((f) => (
          <div key={`${f.group}-${f.path}`} className="ide-git-file">
            <span className="ide-git-status">{f.status}</span>
            <button type="button" className="ide-git-file-name" onClick={() => openChangedFile(f.path)}>
              {f.path.split("/").pop()}
            </button>
            <button type="button" onClick={() => showDiff(f.path)} title="View diff">
              <FileDiff size={12} />
            </button>
          </div>
        ))}
      </div>

      <div className="ide-git-commit">
        <input
          value={commitMsg}
          onChange={(e) => setCommitMsg(e.target.value)}
          placeholder="Commit message"
          onKeyDown={(e) => e.key === "Enter" && commit()}
        />
        <div className="ide-git-commit-actions">
          <button type="button" onClick={stageAll}>Stage all</button>
          <button type="button" onClick={commit} disabled={!commitMsg.trim()}>
            <GitCommit size={12} /> Commit
          </button>
        </div>
      </div>
    </div>
  );
}
