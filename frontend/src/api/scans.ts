import { request } from "./client";

export interface Scan {
  id: string;
  target_id: string;
  status?: string;
  started_at?: string;
  completed_at?: string;
}

export interface StartScanPayload {
  target_id: string;
}

export async function startScan(payload: StartScanPayload) {
  return request<Scan>("/scans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getScan(scanId: string) {
  return request<Scan>(`/scans/${scanId}`);
}

export async function getScans(targetId?: string) {
  const query = targetId
    ? `?target_id=${encodeURIComponent(targetId)}`
    : "";

  return request<Scan[]>(`/scans${query}`);
}

export async function getAttackLogs(scanId: string) {
  return request(`/scans/${scanId}/attack-logs`);
}