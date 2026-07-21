/* Model list page — available AI models */ "use client";
import { useEffect, useState } from "react";
import { Layout } from "@/app/components/Layout";
import { getHeaders, apiUrl } from "@/app/api/api";
type Model = {
  id: string;
  provider: string;
  name: string;
  label: string;
  status: string;
  base_url: string;
  context: string;
  type: string;
};
export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch(apiUrl("/api/v1/models"), { headers: getHeaders() });
        if (!res.ok) throw new Error("Gagal load models");
        const data = await res.json();
        setModels(data.models ?? []);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Error");
      } finally {
        setLoading(false);
      }
    };
    fetchModels();
  }, []);
  const configured = models.filter((m) => m.status === "configured").length;
  const missing = models.filter((m) => m.status === "missing_key").length;
  return (
    <Layout>
      <div className="opsora-container px-4 py-6">
        <div className="opsora-header mb-6">
          <div>
            <h1 className="text-lg font-bold text-white/90 tracking-tight">AI Models</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {configured} configured · {missing} missing key · {models.length} total
            </p>
          </div>
        </div>
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-14 rounded-xl bg-slate-800/50 animate-pulse" />
            ))}
          </div>
        )}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        {!loading && !error && (
          <div className="space-y-2">
            {models.map((m) => (
              <div key={m.id} className="opsora-glass p-3 flex items-center gap-3">
                <div
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    m.status === "configured" ? "bg-emerald-400" : "bg-red-400"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white/90">{m.name}</span>
                    <span className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded-full">
                      {m.context}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {m.provider} · {m.label}
                  </div>
                </div>
                <div className="text-right">
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      m.status === "configured"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {m.status === "configured" ? "Ready" : "Missing key"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
