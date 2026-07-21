"use client";

const STATUS_MAP: Record<string, { dot: string; tag: string; label: string }> = {
  up: { dot: "dot-ok", tag: "tag-ok", label: "UP" },
  running: { dot: "dot-ok", tag: "tag-ok", label: "RUNNING" },
  online: { dot: "dot-ok", tag: "tag-ok", label: "ONLINE" },
  down: { dot: "dot-err", tag: "tag-err", label: "DOWN" },
  offline: { dot: "dot-err", tag: "tag-err", label: "OFFLINE" },
  error: { dot: "dot-err", tag: "tag-err", label: "ERROR" },
  failed: { dot: "dot-err", tag: "tag-err", label: "FAILED" },
  warning: { dot: "dot-warn", tag: "tag-warn", label: "WARN" },
  pending: { dot: "dot-warn dot-pulse", tag: "tag-warn", label: "PENDING" },
  planning: { dot: "dot-warn dot-pulse", tag: "tag-warn", label: "PLANNING" },
  unknown: { dot: "dot-idle", tag: "tag-neutral", label: "UNKNOWN" },
  done: { dot: "dot-ok", tag: "tag-ok", label: "DONE" },
  completed: { dot: "dot-ok", tag: "tag-ok", label: "DONE" },
  provisioning: { dot: "dot-warn dot-pulse", tag: "tag-info", label: "PROV" },
};

export function StatusDot({ status, pulse = false }: { status: string; pulse?: boolean }) {
  const s = STATUS_MAP[status?.toLowerCase()] ?? STATUS_MAP.unknown;
  return <span className={`dot ${s.dot} ${pulse ? "dot-pulse" : ""}`} />;
}

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_MAP[status?.toLowerCase()] ?? STATUS_MAP.unknown;
  return (
    <span className={`tag ${s.tag}`}>
      <span className={`dot ${s.dot}`} />
      {s.label}
    </span>
  );
}
