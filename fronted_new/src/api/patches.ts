import { request } from "./client";

export interface RemediationPatch {
  id: string;
  vulnerability_id: string;
  summary?: string;
  explanation?: string;
  patch_type?: string;
  patch_content?: string;
  created_at?: string;
}

export async function generatePatch(
  vulnerabilityId: string
) {
  return request<RemediationPatch>(
    `/patches/generate/${vulnerabilityId}`,
    {
      method: "POST",
    }
  );
}

export async function getPatches(
  vulnerabilityId: string
) {
  return request<RemediationPatch[]>(
    `/patches/${vulnerabilityId}`
  );
}