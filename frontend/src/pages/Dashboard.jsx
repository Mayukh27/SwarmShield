import { useState } from "react";
import { api } from "../lib/api";
import { useScanStore } from "../store/scanStore";
import { useScanStream } from "../hooks/useScanStream";
import TargetPanel from "../components/TargetPanel";
import ScorecardCard from "../components/ScorecardCard";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel";
import VulnerabilityTable from "../components/VulnerabilityTable";
import AgentLogConsole from "../components/AgentLogConsole";
import AttackFlowCanvas from "../components/flow/AttackFlowCanvas";
import MemoryPanel from "../components/MemoryPanel";
import AttackDnaPanel from "../components/AttackDnaPanel";

export default function Dashboard() {
  const activeScan = useScanStore((s) => s.activeScan);
  const startNewScan = useScanStore((s) => s.startNewScan);
  const [starting, setStarting] = useState(false);

  useScanStream(activeScan?.id);

  const scanInFlight =
    starting || activeScan?.status === "planning" || activeScan?.status === "attacking";

  const handleStartScan = async (targetId) => {
    if (!targetId) return;
    setStarting(true);
    try {
      const scan = await api.startScan(targetId);
      startNewScan(scan);
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-void">
      <header className="flex shrink-0 items-center justify-between border-b border-grid px-6 py-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded border border-amber/40 bg-amber-dim">
            <span className="h-1.5 w-1.5 rounded-full bg-amber" />
          </div>
          <span className="font-display text-sm font-bold tracking-wide text-text-primary">
            SWARM<span className="text-amber">SHIELD</span>
          </span>
        </div>
        <span className="font-mono text-[11px] text-text-muted">
          autonomous agentic AI red-team
        </span>
      </header>

      <main className="grid flex-1 grid-cols-[280px_1fr_360px] gap-4 overflow-hidden p-4">
        <div className="flex flex-col gap-4 overflow-y-auto">
          <TargetPanel onStartScan={handleStartScan} scanInFlight={scanInFlight} />
          <ScorecardCard />
          <RiskBreakdownPanel />
          <div className="flex-1 overflow-y-auto">
            <VulnerabilityTable />
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-4">
          <div className="min-h-0 flex-[2]">
            <AttackFlowCanvas />
          </div>
          <div className="grid shrink-0 grid-cols-2 gap-4">
            <MemoryPanel />
            <AttackDnaPanel />
          </div>
        </div>

        <div className="min-h-0">
          <AgentLogConsole />
        </div>
      </main>
    </div>
  );
}
