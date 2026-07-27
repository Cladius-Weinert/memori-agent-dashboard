"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, File, Folder } from "lucide-react";
import { fetcher } from "@/app/api/api";
import { useIDEStore } from "@/app/stores/ideStore";

type TreeEntry = {
  name: string;
  path: string;
  type: "file" | "dir";
  size?: number;
  children?: TreeEntry[];
};

function TreeNode({ entry, depth = 0 }: { entry: TreeEntry; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);
  const openFile = useIDEStore((s) => s.openFile);
  const activePath = useIDEStore((s) => s.activePath);

  const onClick = async () => {
    if (entry.type === "dir") {
      setOpen(!open);
      return;
    }
    try {
      const data = await fetcher<{ content: string }>(`/api/v1/files/read?path=${encodeURIComponent(entry.path)}`);
      openFile(entry.path, data.content);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <button
        type="button"
        onClick={onClick}
        className="ide-tree-item"
        style={{
          paddingLeft: 8 + depth * 12,
          color: activePath === entry.path ? "var(--accent)" : "var(--t2)",
        }}
      >
        {entry.type === "dir" ? (
          open ? <ChevronDown size={12} /> : <ChevronRight size={12} />
        ) : (
          <span style={{ width: 12 }} />
        )}
        {entry.type === "dir" ? <Folder size={13} /> : <File size={13} />}
        <span className="truncate">{entry.name}</span>
      </button>
      {entry.type === "dir" && open && entry.children?.map((child) => (
        <TreeNode key={child.path} entry={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export function FileTree() {
  const [entries, setEntries] = useState<TreeEntry[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetcher<{ entries: TreeEntry[] }>("/api/v1/files/tree")
      .then((d) => setEntries(d.entries))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-3 text-xs text-red-400">{error}</div>;

  return (
    <div className="ide-tree">
      {entries.map((e) => (
        <TreeNode key={e.path} entry={e} />
      ))}
    </div>
  );
}
