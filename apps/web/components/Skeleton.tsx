/* Loading skeleton component */
"use client";
export function CardSkeleton() {
  return (
    <div className="skeleton-card animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg bg-slate-700" />
        <div className="h-4 w-32 bg-slate-700 rounded" />
      </div>
      <div className="h-3 w-48 bg-slate-700/60 rounded mb-2" />
      <div className="h-3 w-24 bg-slate-700/40 rounded" />
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-6 w-48 bg-slate-700 rounded-lg" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-slate-800/60 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-slate-800/40 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

export function ChatSkeleton() {
  return (
    <div className="space-y-4 p-4 animate-pulse">
      <div className="flex justify-start">
        <div className="bg-slate-800 rounded-2xl rounded-bl-sm p-4 max-w-[80%]">
          <div className="h-3 w-48 bg-slate-700 rounded mb-2" />
          <div className="h-3 w-32 bg-slate-700 rounded" />
        </div>
      </div>
      <div className="flex justify-end">
        <div className="bg-brand-600/30 rounded-2xl rounded-br-sm p-4 max-w-[80%]">
          <div className="h-3 w-40 bg-slate-600 rounded" />
        </div>
      </div>
      <div className="flex justify-start">
        <div className="bg-slate-800 rounded-2xl rounded-bl-sm p-4 max-w-[80%]">
          <div className="h-3 w-36 bg-slate-700 rounded mb-2" />
          <div className="h-3 w-24 bg-slate-700 rounded" />
        </div>
      </div>
    </div>
  );
}