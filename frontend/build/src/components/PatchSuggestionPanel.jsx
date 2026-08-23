import { useState } from "react";
import { api } from "../lib/api";
import { useScanStore } from "../store/scanStore";
import { refreshScanData } from "../lib/refreshScan";

const PATCH_TYPE_LABEL = {
  system_prompt: "System Prompt",
  input_validation: "Input Validation",
  permission_scope: "Permission Scope",
  code: "Code Fix",
};

const RESULT_STYLE = {
  fixed: "text-cyan bg-cyan-dim border-cyan/30",
  still_vulnerable: "text-critical bg-critical-dim border-critical/40",
  inconclusive: "text-amber bg-amber-dim border-amber/30",
};

export default function PatchSuggestionPanel({ patch, vulnerabilityId, target }) {
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [actionResult, setActionResult] = useState(null);
  const activeScanId = useScanStore((s) => s.activeScan?.id);
  const copy = () => navigator.clipboard.writeText(patch.patch_content);
  const isPublic = target?.code_visibility === "public";
  const isPrivateWritable = target?.code_visibility === "private" && target?.access_mode === "read_write";
  const canCreatePr = Boolean(target?.allow_pr_creation);
  const canWriteBranch = isPrivateWritable && Boolean(target?.allow_branch_write);
  const canLiveApply = target?.access_mode === "read_write" && Boolean(target?.allow_direct_patch_apply);
  const readOnlySuggestion = !canCreatePr && !canWriteBranch;

  const runPatchAction = async (action) => {
    setBusy(true);
    setActionResult(null);
    try {
      const result =
        action === "branch"
          ? await api.writeRemediationBranch(patch.id)
          : await api.createRemediationPr(patch.id);
      setActionResult(result.pr_url ? `PR opened: ${result.pr_url}` : `Branch ready: ${result.branch_name}`);
    } catch (e) {
      setActionResult(e.message);
    } finally {
      setBusy(false);
    }
  };

  const applyAndRevalidate = async () => {
    setBusy(true);
    try {
      // Real HTTP round trip: apply this patch to the live target, then
      // replay the exact payload that originally proved the finding and
      // re-run it through the Sentinel — see
      // app/services/revalidation_service.py. This also recomputes the
      // scan's risk score server-side now that the finding's status changed.
      await api.applyAndRevalidate(vulnerabilityId, patch.id, true);
      const records = await api.getRevalidationHistory(vulnerabilityId);
      setHistory(records);

      // The scan's SSE stream has already closed by the time you're
      // applying a patch (that only happens after the scan completes), so
      // nothing pushes the updated risk_score / vulnerability status to the
      // frontend automatically. Pull it explicitly — this is what makes the
      // scorecard actually drop after a fix instead of staying frozen.
      await refreshScanData(activeScanId);
    } catch (e) {
      console.error("Revalidation failed", e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-cyan/30 bg-cyan-dim/60 p-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-cyan">
          {PATCH_TYPE_LABEL[patch.patch_type] || patch.patch_type}
        </span>
        <button
          onClick={copy}
          className="font-mono text-[11px] text-text-muted hover:text-cyan"
        >
          Copy
        </button>
      </div>
      <p className="mt-1.5 text-sm font-medium text-text-primary">{patch.summary}</p>
      <p className="mt-1 text-xs text-text-muted">{patch.explanation}</p>
      <pre className="mt-2 overflow-x-auto rounded border border-grid bg-panel p-2.5 font-mono text-[11px] text-text-primary">
        {patch.patch_content}
      </pre>

      <div className="mt-2.5 flex flex-wrap gap-2">
        {canCreatePr && (
          <button
            onClick={() => runPatchAction("pr")}
            disabled={busy}
            className="rounded border border-gold/40 bg-gold-dim px-3 py-1.5 font-mono text-xs font-medium text-gold transition-colors hover:bg-gold/20 disabled:opacity-50"
          >
            {isPublic ? "Fix codebase & raise PR" : "Raise PR"}
          </button>
        )}
        {canWriteBranch && (
          <button
            onClick={() => runPatchAction("branch")}
            disabled={busy}
            className="rounded border border-amber/40 bg-amber-dim px-3 py-1.5 font-mono text-xs font-medium text-amber transition-colors hover:bg-amber/20 disabled:opacity-50"
          >
            Write new branch
          </button>
        )}
        {readOnlySuggestion && (
          <a
            href={api.patchSuggestionPdfUrl(patch.id)}
            className="rounded border border-cyan/40 bg-cyan/10 px-3 py-1.5 font-mono text-xs font-medium text-cyan transition-colors hover:bg-cyan/20"
          >
            Download fix suggestion PDF
          </a>
        )}
        {canLiveApply && (
          <button
            onClick={applyAndRevalidate}
            disabled={busy}
            className="rounded border border-cyan/40 bg-cyan/10 px-3 py-1.5 font-mono text-xs font-medium text-cyan transition-colors hover:bg-cyan/20 disabled:opacity-50"
          >
            {busy ? "Applying + re-testing target…" : "Apply live patch & re-validate"}
          </button>
        )}
      </div>

      {actionResult && (
        <div className="mt-2 rounded border border-grid bg-panel px-2 py-1 font-mono text-[11px] text-text-muted">
          {actionResult}
        </div>
      )}

      {history.length > 0 && (
        <div className="mt-2 space-y-1">
          {history.map((r) => (
            <div
              key={r.id}
              className={`rounded border px-2 py-1 font-mono text-[11px] ${
                RESULT_STYLE[r.result] || RESULT_STYLE.inconclusive
              }`}
            >
              {r.result === "fixed" ? "✓ FIXED" : r.result === "still_vulnerable" ? "✗ STILL VULNERABLE" : "? INCONCLUSIVE"}
              {" — "}
              replay re-tested against the live target
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
