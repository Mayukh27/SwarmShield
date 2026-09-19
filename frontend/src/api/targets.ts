import { request } from "./client";

export interface Target {
  id: string;
  name?: string;
  url?: string;
  target?: string;
  description?: string;
  authorized: boolean;
  created_at?: string;
}

export interface CreateTargetPayload {
  name?: string;
  url?: string;
  target?: string;
  description?: string;
  authorized: boolean;
}

export async function getTargets() {
  return request<Target[]>("/targets");
}

export async function createTarget(
  payload: CreateTargetPayload
) {
  return request<Target>("/targets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteTarget(id: string) {
  return request<void>(`/targets/${id}`, {
    method: "DELETE",
  });
}