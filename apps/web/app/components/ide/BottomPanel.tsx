"use client";

import dynamic from "next/dynamic";
import { useIDEStore } from "@/app/stores/ideStore";
import { wsUrl } from "@/app/api/api";

const XTermTerminal = dynamic(() => import("@/components/XTermTerminal"), { ssr: false });

export function BottomPanel() {
  const bottomTab = useIDEStore((s) => s.bottomTab);
  const setBottomTab = useIDEStore((s) => s.setBottomTab);
  const terminalInstanceId = useIDEStore((s) => s.terminalInstanceId);

  return (
    <div className="ide-bottom">
      <div className="ide-bottom-tabs">
        <button
          type="button"
          className={bottomTab === "terminal" ? "active" : ""}
          onClick={() => setBottomTab("terminal")}
        >
          Terminal
        </button>
        <button
          type="button"
          className={bottomTab === "output" ? "active" : ""}
          onClick={() => setBottomTab("output")}
        >
          Output
        </button>
      </div>
      <div className="ide-bottom-body">
        {bottomTab === "terminal" ? (
          terminalInstanceId ? (
            <XTermTerminal wsUrl={wsUrl(terminalInstanceId)} className="h-full min-h-[180px]" />
          ) : (
            <div className="ide-bottom-placeholder">
              Buka instance di /instances untuk SSH terminal, atau jalankan agent command.
            </div>
          )
        ) : (
          <div className="ide-bottom-placeholder mono text-xs">
            Git diff review muncul di editor saat Save. Agent output di panel kanan.
          </div>
        )}
      </div>
    </div>
  );
}
