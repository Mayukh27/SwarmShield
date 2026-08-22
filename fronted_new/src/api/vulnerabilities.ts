import { request } from "./client";

export interface Vulnerability {
  id: string;
  scan_id?: string;
  title: string;
  description?: string;
  severity?: string;
  cvss?: number;
  owasp_category?: string;
  created_at?: string;
}

export async function getVulnerabilities(
  scanId?: string
) {
  const query = scanId
    ? `?scan_id=${encodeURIComponent(scanId)}`
    : "";

  return request<Vulnerability[]>(
    `/vulnerabilities${query}`
  );
}

export async function getVulnerability(id: string) {
  return request<Vulnerability>(
    `/vulnerabilities/${id}`
  );
}