import { useState, useEffect } from "react";
import { api } from "./lib/api";
import { useScanStore } from "./store/scanStore";
import { useScanStream } from "./hooks/useScanStream";
import Atmosphere from "./components/ui/Atmosphere";
import Header from "./components/hud/Header";
import BottomNav from "./components/hud/BottomNav";
import Sidebar from "./components/hud/Sidebar";
import Dashboard from "./screens/Dashboard";
import Agents from "./screens/Agents";
import RealmRegistry from "./screens/RealmRegistry";
import Intelligence from "./screens/Intelligence";
<<<<<<< Updated upstream
import LiveSiege from "./screens/LiveSiege";
import SiegeReport from "./screens/SiegeReport";
import RemediationForge from "./screens/RemediationForge";
import Timeline from "./screens/Timeline";
import Outcome from "./screens/Outcome";
=======
import SiegeReport from "./screens/SiegeReport";
import RemediationForge from "./screens/RemediationForge";
import Reports from "./screens/Reports";
>>>>>>> Stashed changes
import Settings from "./screens/Settings";
import WarRoom from "./screens/WarRoom";
import LiveSiege from "./screens/LiveSiege";
import Outcome from "./screens/Outcome";
import Timeline from "./screens/Timeline";

const TITLES = {
  dashboard: { eyebrow: "SECURITY OPERATIONS", title: "Command Center" },
  agents: { eyebrow: "SECURITY OPERATIONS", title: "AI Agents" },
  targets: { eyebrow: "SECURITY OPERATIONS", title: "Targets" },
  vulnerabilities: { eyebrow: "SECURITY OPERATIONS", title: "Vulnerabilities" },
  patches: { eyebrow: "SECURITY OPERATIONS", title: "Patch Center" },
  reports: { eyebrow: "SECURITY OPERATIONS", title: "Reports" },
  intel: { eyebrow: "SECURITY OPERATIONS", title: "Capability Intelligence" },
  settings: { eyebrow: "ACCOUNT", title: "Settings" },
  warroom: { eyebrow: "SIEGE MODE", title: "War Room" },
  siege: { eyebrow: "SIEGE MODE", title: "Live Siege" },
  outcome: { eyebrow: "SIEGE MODE", title: "Outcome" },
  timeline: { eyebrow: "SECURITY OPERATIONS", title: "War Log" },
};

// WarRoom/LiveSiege/Outcome are ported straight from the original siege-mode
// build, where they navigate each other by their own screen ids ("registry",
// "forge", "siege", "warroom", "outcome"). Rather than rewrite their working
// navigation calls, this shell maps the couple of ids that don't already
// match the SOC screen ids ("registry" -> targets, "forge" -> patches) so
// every existing onNavigate("...") call in those screens keeps working
// unchanged.
const LEGACY_NAV_MAP = { registry: "targets", forge: "patches" };

export default function AppShell() {
  const activeScan = useScanStore((s) => s.activeScan);
  const targets = useScanStore((s) => s.targets);
  const selectedTargetId = useScanStore((s) => s.selectedTargetId);
  const startNewScan = useScanStore((s) => s.startNewScan);
  const [starting, setStarting] = useState(false);
  const [screen, setScreen] = useState("dashboard");
  const [declareWarError, setDeclareWarError] = useState(null);

  // Identical real-time wiring to the original Dashboard.jsx — SSE stream
  // subscribes whenever there's an active scan id, regardless of which
  // screen is currently showing, so events keep flowing in the background.
  useScanStream(activeScan?.id);

  const scanInFlight =
    starting || activeScan?.status === "planning" || activeScan?.status === "attacking";

  const goToScreen = (id) => setScreen(LEGACY_NAV_MAP[id] || id);

  const handleDeclareWar = async (targetId) => {
    if (!targetId) return;
    setStarting(true);
    setDeclareWarError(null);
    try {
      const scan = await api.startScan(targetId);
      startNewScan(scan);
      setScreen("agents");
    } catch (e) {
      // Backend refuses to scan a target that isn't attested authorized
      // (403, see api/routes/scans.py) — that refusal needs to actually
      // reach the person clicking the button, not fail silently, since the
      // whole point of the guard is to make an unauthorized attempt a
      // visible, deliberate act rather than a shrug.
      setDeclareWarError(e.message || "Could not start the scan.");
    } finally {
      setStarting(false);
    }
  };

  // Auto-advance to Reports the moment a running scan finishes, so the
  // outcome isn't missed if the user wandered to another screen.
  useEffect(() => {
    if (
      screen === "agents" &&
      activeScan &&
      (activeScan.status === "completed" || activeScan.status === "failed")
    ) {
      const t = setTimeout(() => setScreen("reports"), 3200);
      return () => clearTimeout(t);
    }
  }, [activeScan?.status, screen]); // eslint-disable-line react-hooks/exhaustive-deps

  const meta = TITLES[screen] || TITLES.dashboard;

  return (
    <div className="relative flex h-screen bg-void">
      {/* Concept-style atmospheric background — fixed, z-0, pointer-events:none.
          Sidebar and the content wrapper below are explicitly z-10 so they
          always render above it and it can never cover or block the UI. */}
      <Atmosphere />
      <Sidebar screen={screen} onNavigate={goToScreen} />
      <div className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header
          eyebrow={meta.eyebrow}
          title={meta.title}
          onNewScan={() => handleDeclareWar(selectedTargetId || targets[0]?.id)}
          scanInFlight={scanInFlight}
          onOpenSettings={() => setScreen("settings")}
        />
        {declareWarError && (
          <div className="flex shrink-0 items-center justify-between border-b border-critical/40 bg-critical-dim px-5 py-2">
            <span className="text-[11px] text-critical">⚠ {declareWarError}</span>
            <button
              onClick={() => setDeclareWarError(null)}
              className="text-[11px] text-critical hover:underline"
            >
              Dismiss
            </button>
          </div>
        )}
<<<<<<< Updated upstream
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
=======
        <main className="min-h-0 flex-1 overflow-y-auto">
          {screen === "dashboard" && (
            <Dashboard onNavigate={goToScreen} onDeclareWar={handleDeclareWar} scanInFlight={scanInFlight} />
          )}
          {screen === "agents" && <Agents scanInFlight={scanInFlight} />}
          {screen === "targets" && (
            <RealmRegistry onDeclareWar={handleDeclareWar} scanInFlight={scanInFlight} />
          )}
          {screen === "vulnerabilities" && <SiegeReport onNavigate={goToScreen} />}
          {screen === "patches" && <RemediationForge />}
          {screen === "reports" && <Reports />}
          {screen === "intel" && <Intelligence />}
          {screen === "settings" && <Settings />}
          {screen === "warroom" && (
            <WarRoom onNavigate={goToScreen} onDeclareWar={handleDeclareWar} scanInFlight={scanInFlight} />
          )}
          {screen === "siege" && <LiveSiege onNavigate={goToScreen} />}
          {screen === "outcome" && <Outcome onNavigate={goToScreen} />}
          {screen === "timeline" && <Timeline />}
        </main>
        <BottomNav screen={screen} onNavigate={goToScreen} />
      </div>
>>>>>>> Stashed changes
    </div>
  );
}
