import { useState, useEffect } from "react";
import { api } from "./lib/api";
import { useScanStore } from "./store/scanStore";
import { useScanStream } from "./hooks/useScanStream";
import TopHUD from "./components/hud/TopHUD";
import BottomNav from "./components/hud/BottomNav";
import WarRoom from "./screens/WarRoom";
import RealmRegistry from "./screens/RealmRegistry";
import Intelligence from "./screens/Intelligence";
import LiveSiege from "./screens/LiveSiege";
import SiegeReport from "./screens/SiegeReport";
import RemediationForge from "./screens/RemediationForge";
import Timeline from "./screens/Timeline";
import Outcome from "./screens/Outcome";
import Settings from "./screens/Settings";

export default function AppShell() {
  const activeScan = useScanStore((s) => s.activeScan);
  const startNewScan = useScanStore((s) => s.startNewScan);
  const [starting, setStarting] = useState(false);
  const [screen, setScreen] = useState("warroom");
  const [declareWarError, setDeclareWarError] = useState(null);

  // Identical real-time wiring to the original Dashboard.jsx — SSE stream
  // subscribes whenever there's an active scan id, regardless of which
  // screen is currently showing, so events keep flowing in the background.
  useScanStream(activeScan?.id);

  const scanInFlight =
    starting || activeScan?.status === "planning" || activeScan?.status === "attacking";

  const handleDeclareWar = async (targetId) => {
    if (!targetId) return;
    setStarting(true);
    setDeclareWarError(null);
    try {
      const scan = await api.startScan(targetId);
      startNewScan(scan);
      setScreen("siege");
    } catch (e) {
      // Backend refuses to scan a target that isn't attested authorized
      // (403, see api/routes/scans.py) — that refusal needs to actually
      // reach the person clicking the button, not fail silently, since the
      // whole point of the guard is to make an unauthorized attempt a
      // visible, deliberate act rather than a shrug.
      setDeclareWarError(e.message || "Could not start the siege.");
    } finally {
      setStarting(false);
    }
  };

  // Auto-advance to the Outcome screen the moment a running siege finishes,
  // so the payoff isn't missed if the user wandered to another tab.
  useEffect(() => {
    if (
      screen === "siege" &&
      activeScan &&
      (activeScan.status === "completed" || activeScan.status === "failed")
    ) {
      const t = setTimeout(() => setScreen("outcome"), 3200);
      return () => clearTimeout(t);
    }
  }, [activeScan?.status, screen]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-screen flex-col bg-void">
      <TopHUD />
      {declareWarError && (
        <div className="flex shrink-0 items-center justify-between border-b border-critical/40 bg-critical-dim px-5 py-2">
          <span className="font-mono text-[11px] text-critical">⚠ {declareWarError}</span>
          <button
            onClick={() => setDeclareWarError(null)}
            className="font-mono text-[11px] text-critical hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}
      <main className="min-h-0 flex-1 overflow-hidden">
        {screen === "warroom" && (
          <WarRoom onNavigate={setScreen} onDeclareWar={handleDeclareWar} scanInFlight={scanInFlight} />
        )}
        {screen === "registry" && (
          <RealmRegistry onDeclareWar={handleDeclareWar} scanInFlight={scanInFlight} />
        )}
        {screen === "intel" && <Intelligence />}
        {screen === "siege" && <LiveSiege onNavigate={setScreen} />}
        {screen === "report" && <SiegeReport onNavigate={setScreen} />}
        {screen === "forge" && <RemediationForge />}
        {screen === "timeline" && <Timeline />}
        {screen === "outcome" && <Outcome onNavigate={setScreen} />}
        {screen === "settings" && <Settings />}
      </main>
      <BottomNav screen={screen} onNavigate={setScreen} hasActiveScan={!!activeScan} />
    </div>
  );
}
