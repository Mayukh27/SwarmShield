import { CATEGORY_TO_STRUCTURE, AGENT_TO_TROOP } from "../theme/coc";

export default function Settings() {
  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col gap-5 overflow-y-auto px-5 py-6">
      <div>
        <h1 className="font-display text-lg font-bold text-text-primary">⚙️ Settings & Glossary</h1>
        <p className="font-mono text-[11px] text-text-muted">
          SwarmShield uses a Clash-of-Clans-style theme purely as visual flavor. Every icon and
          game term below maps to one real, specific thing in the system — nothing on screen is
          decoration without a real meaning behind it.
        </p>
      </div>

      <section className="rounded-lg border border-grid bg-panel p-4">
        <h2 className="font-display text-xs font-semibold tracking-widest text-text-muted">
          FORTRESS &amp; TROOPS
        </h2>
        <dl className="mt-3 flex flex-col gap-2 font-mono text-xs">
          <Row icon="🏰" term="Fortress / Realm" real="The AI system you registered to test (a TargetProfile)" />
          <Row icon="🛡️" term="Fortress Integrity" real="Security score, 100 minus the real risk score" />
          <Row icon="⚔️" term="Declare War / Siege" real="Starts a real automated scan against the target" />
          <Row icon="🔨" term="The Forge" real="Where AI-generated remediation patches are created and applied" />
          <Row icon="🏆" term="Victory" real="Every confirmed finding has been patched and re-verified as fixed" />
        </dl>
      </section>

      <section className="rounded-lg border border-grid bg-panel p-4">
        <h2 className="font-display text-xs font-semibold tracking-widest text-text-muted">
          TROOPS = ATTACK AGENTS
        </h2>
        <dl className="mt-3 flex flex-col gap-2 font-mono text-xs">
          {Object.entries(AGENT_TO_TROOP).map(([key, t]) => (
            <Row key={key} icon={t.icon} term={t.troop} real={t.role} />
          ))}
        </dl>
      </section>

      <section className="rounded-lg border border-grid bg-panel p-4">
        <h2 className="font-display text-xs font-semibold tracking-widest text-text-muted">
          STRUCTURES = OWASP LLM TOP-10 CATEGORIES
        </h2>
        <dl className="mt-3 flex flex-col gap-2 font-mono text-xs">
          {Object.entries(CATEGORY_TO_STRUCTURE).map(([cat, s]) => (
            <Row key={cat} icon={s.icon} term={s.structure} real={cat} />
          ))}
        </dl>
      </section>

      <section className="rounded-lg border border-grid bg-panel p-4">
        <h2 className="font-display text-xs font-semibold tracking-widest text-text-muted">ABOUT</h2>
        <p className="mt-2 font-mono text-[11px] leading-relaxed text-text-muted">
          SwarmShield is an autonomous multi-agent red-teaming framework for AI systems. A swarm
          of specialist attacker agents, coordinated by a Planner and judged in real time by a
          Sentinel, tests a target AI for real OWASP LLM Top-10 vulnerabilities, then drafts and
          verifies patches — no scripted demo data anywhere in this build.
        </p>
      </section>
    </div>
  );
}

function Row({ icon, term, real }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="w-5 shrink-0 text-center">{icon}</span>
      <span className="w-32 shrink-0 font-semibold text-text-primary">{term}</span>
      <span className="text-text-muted">{real}</span>
    </div>
  );
}
