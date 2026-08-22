import { useScanStore } from "../store/scanStore";

export default function AttackDnaPanel() {
  const attackDna = useScanStore((s) => s.attackDna);

  const byVector = attackDna.reduce((acc, d) => {
    (acc[d.vector_id] ||= []).push(d);
    return acc;
  }, {});

  return (
    <div className="rounded-lg border border-grid bg-panel">
      <div className="border-b border-grid px-4 py-2.5 font-display text-xs font-semibold tracking-widest text-text-muted">
        ATTACK DNA
      </div>
      <div className="max-h-64 overflow-y-auto divide-y divide-grid">
        {Object.keys(byVector).length === 0 ? (
          <p className="px-4 py-3 text-sm text-text-muted">
            No attack DNA yet — seeded per vector, mutated by the Sentinel's
            hint on each retry.
          </p>
        ) : (
          Object.entries(byVector).map(([vectorId, generations]) => (
            <div key={vectorId} className="px-4 py-2.5">
              <div className="font-mono text-[11px] text-text-muted">{vectorId}</div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {generations
                  .sort((a, b) => a.generation - b.generation)
                  .map((gen, i) => (
                    <span key={gen.id} className="flex items-center gap-1.5">
                      {i > 0 && <span className="text-text-muted">→</span>}
                      <span
                        title={JSON.stringify(gen.genome)}
                        className="rounded border border-amber/30 bg-amber-dim px-1.5 py-0.5 font-mono text-[10px] text-amber"
                      >
                        gen{gen.generation} ({Math.round(gen.success_probability * 100)}%)
                      </span>
                    </span>
                  ))}
              </div>
              {generations.length > 1 && (
                <p className="mt-1 text-[11px] text-text-muted">
                  last mutation:{" "}
                  {generations[generations.length - 1].mutations?.slice(-1)[0]?.mutation_type}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
