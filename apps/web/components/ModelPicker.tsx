/* Model picker — slide-up sheet for switching AI models */
"use client";
import { useState } from "react";
import { ChevronDown, Check } from "lucide-react";

const MODELS = [
  { id: "nvidia-llama", provider: "NVIDIA", name: "Llama-3.1-70B", label: "Best balance", color: "bg-emerald-500" },
  { id: "alibaba-qwen", provider: "Alibaba", name: "Qwen2.5-72B", label: "Large context", color: "bg-violet-500" },
  { id: "tokenhub", provider: "TokenHub", name: "DeepSeek-V3", label: "Fast reasoning", color: "bg-orange-500" },
  { id: "bedrock", provider: "AWS Bedrock", name: "Claude Sonnet", label: "Production", color: "bg-blue-500" },
  { id: "local", provider: "Local", name: "Ollama", label: "Free, private", color: "bg-slate-500" },
];

export function ModelPicker({ selected, onSelect }: {
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = MODELS.find((m) => m.id === selected) ?? MODELS[0];

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="model-picker-trigger"
        aria-label="Select AI model"
      >
        <span className={`w-2 h-2 rounded-full ${current.color}`} />
        <span className="text-sm font-medium">{current.name}</span>
        <ChevronDown size={14} className="text-slate-400" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-lg bg-slate-900 rounded-t-2xl border-t border-slate-700 p-4 pb-8 animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-10 h-1 bg-slate-600 rounded-full mx-auto mb-4" />
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Choose Model</h3>
            <div className="space-y-2">
              {MODELS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => { onSelect(m.id); setOpen(false); }}
                  className={`model-option ${selected === m.id ? "selected" : ""}`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-2.5 h-2.5 rounded-full ${m.color}`} />
                    <div className="text-left">
                      <div className="text-sm font-medium">{m.name}</div>
                      <div className="text-xs text-slate-500">{m.provider} · {m.label}</div>
                    </div>
                  </div>
                  {selected === m.id && <Check size={16} className="text-brand-400" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}