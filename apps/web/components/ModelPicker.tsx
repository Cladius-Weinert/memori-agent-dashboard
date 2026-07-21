"use client";
import { useState } from "react";
import { ChevronDown } from "lucide-react";

const MODELS = [
  { id: "nvidia-llama", name: "Llama 3.1 70B", provider: "NVIDIA", tier: "fast" },
  { id: "nvidia-nemotron", name: "Nemotron Ultra 253B", provider: "NVIDIA", tier: "max" },
  { id: "nvidia-deepseek", name: "DeepSeek V4 Pro", provider: "NVIDIA", tier: "coder" },
  { id: "alibaba-qwen-max", name: "Qwen 3.7 Max", provider: "Alibaba", tier: "max" },
  { id: "groq-llama", name: "Llama 3.3 70B", provider: "Groq", tier: "fast" },
];

export function ModelPicker({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = MODELS.find((m) => m.id === selected) ?? MODELS[0];

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="model-pill">
        <span className="dot dot-ok" />
        {current.name}
        <ChevronDown size={12} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 top-full mt-1 z-50 w-56 anim-fade"
            style={{
              background: "var(--s2)",
              border: "1px solid var(--b1)",
              borderRadius: "var(--r-md)",
              overflow: "hidden",
            }}
          >
            {MODELS.map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  onSelect(m.id);
                  setOpen(false);
                }}
                className="w-full text-left px-3 py-2.5 flex items-center justify-between transition-colors"
                style={{
                  borderBottom: "1px solid var(--b2)",
                  color: m.id === selected ? "var(--accent)" : "var(--t1)",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--s3)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div>
                  <div className="text-[13px] font-medium">{m.name}</div>
                  <div className="mono text-[11px]" style={{ color: "var(--t3)" }}>
                    {m.provider} · {m.tier}
                  </div>
                </div>
                {m.id === selected && <span className="dot dot-ok" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
