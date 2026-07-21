/* Status badge — colored dots for instance health */
"use client";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  up:      { color: "bg-emerald-400", label: "Online" },
  running: { color: "bg-emerald-400", label: "Running" },
  down:    { color: "bg-red-400",    label: "Offline" },
  unknown: { color: "bg-yellow-400", label: "Unknown" },
  provisioning: { color: "bg-blue-400", label: "Provisioning" },
};

export function StatusDot({ status, pulse = false }: { status: string; pulse?: boolean }) {
  const s = STATUS_MAP[status] ?? { color: "bg-slate-400", label: status };
  return (
    <span className={`inline-block w-2.5 h-2.5 rounded-full ${s.color} ${pulse ? "animate-pulse" : ""}`} />
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_MAP[status] ?? { color: "bg-slate-500", label: status };
  return (
    <span className={`status-badge ${s.color.replace("bg-", "badge-")}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.color} ${status === "provisioning" ? "animate-pulse" : ""}`} />
      {s.label}
    </span>
  );
}