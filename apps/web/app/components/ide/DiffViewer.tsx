"use client";

export type DiffLine = { type: "add" | "del" | "ctx" | "meta" | "hunk"; text: string };

type Props = {
  path?: string;
  lines: DiffLine[];
  onAccept?: () => void;
  onReject?: () => void;
  title?: string;
};

export function DiffViewer({ path, lines, onAccept, onReject, title }: Props) {
  if (!lines.length) {
    return (
      <div className="ide-diff-empty">No changes</div>
    );
  }

  return (
    <div className="ide-diff">
      <div className="ide-diff-header">
        <span>{title ?? `Diff${path ? `: ${path}` : ""}`}</span>
        <div className="ide-diff-actions">
          {onReject && (
            <button type="button" className="ide-diff-btn reject" onClick={onReject}>
              Reject
            </button>
          )}
          {onAccept && (
            <button type="button" className="ide-diff-btn accept" onClick={onAccept}>
              Accept
            </button>
          )}
        </div>
      </div>
      <pre className="ide-diff-body">
        {lines.map((line, i) => (
          <div key={i} className={`ide-diff-line ide-diff-line--${line.type}`}>
            <span className="ide-diff-prefix">
              {line.type === "add" ? "+" : line.type === "del" ? "-" : " "}
            </span>
            <span>{line.text}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}
