const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Targets
  listTargets: () => request("/targets"),
  createTarget: (payload) =>
    request("/targets", { method: "POST", body: JSON.stringify(payload) }),
  deleteTarget: (id) => request(`/targets/${id}`, { method: "DELETE" }),

  // Scans
  startScan: (targetId) =>
    request("/scans", {
      method: "POST",
      body: JSON.stringify({ target_id: targetId }),
    }),
  getScan: (id) => request(`/scans/${id}`),
  getAttackLogs: (scanId) => request(`/scans/${scanId}/attack-logs`),
  scanReportPdfUrl: (scanId) => `${BASE}/scans/${scanId}/report.pdf`,

  // Vulnerabilities
  listVulnerabilities: (scanId) =>
    request(`/vulnerabilities${scanId ? `?scan_id=${scanId}` : ""}`),

  // Patches
  generatePatch: (vulnerabilityId) =>
    request(`/patches/generate/${vulnerabilityId}`, { method: "POST" }),
  listPatches: (vulnerabilityId) => request(`/patches/${vulnerabilityId}`),
  patchSuggestionPdfUrl: (patchId) => `${BASE}/patches/${patchId}/suggestion.pdf`,
  createRemediationPr: (patchId) => request(`/patches/${patchId}/create-pr`, { method: "POST" }),
  writeRemediationBranch: (patchId) => request(`/patches/${patchId}/write-branch`, { method: "POST" }),

  // Memory / Attack DNA / Graph — new panels
  getScanMemory: (scanId) => request(`/scans/${scanId}/memory`),
  getScanDna: (scanId) => request(`/scans/${scanId}/attack-dna`),
  getScanGraph: (scanId) => request(`/scans/${scanId}/graph`),

  // Remediation + re-validation
  applyAndRevalidate: (vulnerabilityId, patchId, apply = true) =>
    request(
      `/vulnerabilities/${vulnerabilityId}/apply-and-revalidate?apply=${apply}${
        patchId ? `&patch_id=${patchId}` : ""
      }`,
      { method: "POST" }
    ),
  getRevalidationHistory: (vulnerabilityId) =>
    request(`/vulnerabilities/${vulnerabilityId}/revalidation-history`),

  // Capability Intelligence — declared/observed/inferred capabilities,
  // ToolFrames, capability graph, attack paths, hypotheses (all in one
  // payload; see backend/app/services/capability_service.py).
  getTargetCapabilities: (targetId, scanId) =>
    request(`/targets/${targetId}/capabilities${scanId ? `?scan_id=${scanId}` : ""}`),
  getCapabilityDiff: (targetId, scanId, compareToScanId) =>
    request(
      `/targets/${targetId}/capabilities/diff?scan_id=${scanId}` +
        (compareToScanId ? `&compare_to_scan_id=${compareToScanId}` : "")
    ),
  getHypothesisRecords: (targetId, scanId) =>
    request(`/targets/${targetId}/capabilities/hypotheses/records?scan_id=${scanId}`),
  approveHypothesis: (targetId, hypothesisId, scanId) =>
    request(`/targets/${targetId}/capabilities/hypotheses/${hypothesisId}/approve?scan_id=${scanId}`, { method: "POST" }),
  skipHypothesis: (targetId, hypothesisId, scanId) =>
    request(`/targets/${targetId}/capabilities/hypotheses/${hypothesisId}/skip?scan_id=${scanId}`, { method: "POST" }),

  // Local-first LLM routing / RAG / memory stats (backend/app/api/routes/intelligence.py)
  getLlmHealth: () => request(`/llm/health`),
  getMemoryStats: () => request(`/memory/stats`),
};

export function scanStreamUrl(scanId) {
  return `${BASE}/scans/${scanId}/stream`;
}
