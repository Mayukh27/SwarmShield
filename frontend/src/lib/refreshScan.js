import { api } from "./api";
import { useScanStore } from "../store/scanStore";

/**
 * Re-pulls attack logs, vulnerabilities, scan status (incl. risk_score),
 * memory, and attack DNA for a scan, and writes them into the store.
 *
 * Used by useScanStream while the SSE connection is open, and also by
 * one-off post-scan actions (e.g. "Apply patch & re-validate") that happen
 * AFTER the scan has completed and the SSE stream has already closed —
 * those actions change a vulnerability's status and the scan's risk_score
 * server-side, but nothing pushes that change to the frontend unless
 * something calls this explicitly.
 */
export async function refreshScanData(scanId) {
  if (!scanId) return;
  const { setAttackLogs, setVulnerabilities, updateScanStatus, setMemory, setAttackDna } =
    useScanStore.getState();

  const [logs, vulns, scan, memory, dna] = await Promise.all([
    api.getAttackLogs(scanId),
    api.listVulnerabilities(scanId),
    api.getScan(scanId),
    api.getScanMemory(scanId),
    api.getScanDna(scanId),
  ]);

  setAttackLogs(logs);
  setVulnerabilities(vulns);
  updateScanStatus(scan);
  setMemory(memory);
  setAttackDna(dna);
}
