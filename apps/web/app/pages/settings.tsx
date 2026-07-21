/* Settings page — premium mobile-first */
"use client";
import { useState } from "react";
import { Layout } from "@/app/components/Layout";
import {
  Cloud,
  Key,
  Shield,
  ChevronRight,
  Terminal,
  Fingerprint,
  Info,
  CheckCircle2,
} from "lucide-react";

const providers = [
  { id: "aws", label: "AWS", icon: Cloud, status: "Configured" as const, color: "text-amber-400" },
  { id: "gcp", label: "GCP", icon: Shield, status: "Configured" as const, color: "text-blue-400" },
  { id: "do", label: "DigitalOcean", icon: Cloud, status: "Connect" as const, color: "text-sky-400" },
  { id: "vultr", label: "Vultr", icon: Cloud, status: "Connect" as const, color: "text-cyan-400" },
];

type ProviderStatus = "Configured" | "Connect"; // eslint-disable-line @typescript-eslint/no-unused-vars

export default function SettingsPage() {
  const [sshKey, setSshKey] = useState("");

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <h1 className="gradient-text text-xl font-bold">Settings</h1>

        {/* Provider Credentials */}
        <section>
          <div className="text-label mb-2">Provider Credentials</div>
          <div className="card divide-y divide-slate-800/50">
            {providers.map((p) => {
              const Icon = p.icon;
              const configured = p.status === "Configured";
              return (
                <div key={p.id} className="flex items-center justify-between py-3 px-0.5 active:scale-[0.99] transition-transform cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-slate-800/60 flex items-center justify-center">
                      <Icon size={16} className={p.color} />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{p.label}</div>
                      <div className={`text-xs mt-px ${configured ? "text-emerald-400" : "text-slate-500"}`}>{p.status}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {configured && <CheckCircle2 size={14} className="text-emerald-500" />}
                    <ChevronRight size={14} className="text-slate-600" />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* SSH Keys */}
        <section>
          <div className="text-label mb-2">SSH Keys</div>
          <div className="card space-y-3">
            <textarea
              className="input min-h-[80px] resize-none"
              placeholder="Paste your public SSH key..."
              value={sshKey}
              onChange={(e) => setSshKey(e.target.value)}
            />
            <div className="text-[11px] text-slate-600 flex items-center gap-1.5">
              <Fingerprint size={12} />
              Used for agent SSH access across all providers
            </div>
          </div>
        </section>

        {/* AI Model */}
        <section>
          <div className="text-label mb-2">AI Model</div>
          <div className="card">
            <div className="flex items-center justify-between active:scale-[0.99] transition-transform cursor-pointer">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-900/30 flex items-center justify-center">
                  <Terminal size={16} className="text-brand-400" />
                </div>
                <div>
                  <div className="text-sm font-medium text-white">NVIDIA Llama-3.1-70B</div>
                  <div className="text-xs text-slate-500 mt-px">Primary agent model</div>
                </div>
              </div>
              <ChevronRight size={14} className="text-slate-600" />
            </div>
          </div>
        </section>

        {/* About */}
        <section>
          <div className="text-label mb-2">About</div>
          <div className="card space-y-2">
            <div className="flex items-center justify-between py-1">
              <span className="text-sm text-slate-400">Version</span>
              <span className="text-sm text-white font-mono">1.0.0</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-sm text-slate-400">Build</span>
              <span className="text-sm text-slate-500 font-mono">2026.07.21</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-sm text-slate-400">Framework</span>
              <span className="text-sm text-slate-500 font-mono">Next.js 14</span>
            </div>
            <div className="flex items-center gap-2 pt-2 text-[11px] text-slate-600 border-t border-slate-800/50">
              <Info size={12} />
              Opsora Agent — multi-cloud infrastructure management
            </div>
          </div>
        </section>

        {/* Footer spacing */}
        <div className="h-8" />
      </div>
    </Layout>
  );
}