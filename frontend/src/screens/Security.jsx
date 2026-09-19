import SecurityPanel from "../components/SecurityPanel";
import AgentLogConsole from "../components/AgentLogConsole";

/** Dedicated A2A Security screen: same panel as on the Agents page, plus the shared Battle Log. */
export default function Security() {
  return (
    <div className="relative min-h-full space-y-6 p-6 lg:p-8">
      <SecurityPanel />
      <div className="glass h-[360px] overflow-hidden rounded-2xl">
        <AgentLogConsole />
      </div>
    </div>
  );
}
