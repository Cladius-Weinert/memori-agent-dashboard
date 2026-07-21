"use client";

export function PanelSkeleton() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="skel" style={{ width: 80, height: 14 }} />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="panel-row" style={{ gap: 12 }}>
          <div className="skel" style={{ width: 32, height: 32, borderRadius: "var(--r-sm)" }} />
          <div className="flex-1 space-y-1">
            <div className="skel" style={{ width: "60%", height: 13 }} />
            <div className="skel" style={{ width: "40%", height: 11 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-5">
      <div className="skel" style={{ width: 160, height: 20 }} />
      <div className="data-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="data-cell">
            <div className="skel" style={{ width: 40, height: 22 }} />
            <div className="skel" style={{ width: 50, height: 11, marginTop: 4 }} />
          </div>
        ))}
      </div>
      <PanelSkeleton />
    </div>
  );
}

export function ChatSkeleton() {
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="skel" style={{ width: 24, height: 24, borderRadius: "var(--r-sm)" }} />
        <div className="skel" style={{ width: "70%", height: 48, borderRadius: "var(--r-md)" }} />
      </div>
      <div className="flex justify-end">
        <div className="skel" style={{ width: "50%", height: 36, borderRadius: "var(--r-md)" }} />
      </div>
      <div className="flex gap-2">
        <div className="skel" style={{ width: 24, height: 24, borderRadius: "var(--r-sm)" }} />
        <div className="skel" style={{ width: "60%", height: 64, borderRadius: "var(--r-md)" }} />
      </div>
    </div>
  );
}
