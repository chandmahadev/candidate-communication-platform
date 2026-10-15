import type { BulkDeleteResponse, Candidate, CandidateInput, Message, MessageStatus } from "@/types";
import { apiRequest } from "./client";

export function listCandidates(search?: string, signal?: AbortSignal): Promise<Candidate[]> {
  return apiRequest<Candidate[]>("/api/candidates/", { query: { search: search?.trim() }, signal });
}

export function getCandidate(id: number, signal?: AbortSignal): Promise<Candidate> {
  return apiRequest<Candidate>(`/api/candidates/${id}/`, { signal });
}

export function createCandidate(input: CandidateInput): Promise<Candidate> {
  return apiRequest<Candidate>("/api/candidates/", { method: "POST", body: input });
}

export function deleteCandidate(id: number): Promise<void> {
  return apiRequest<void>(`/api/candidates/${id}/`, { method: "DELETE" });
}

export function bulkDeleteCandidates(ids: number[]): Promise<BulkDeleteResponse> {
  return apiRequest<BulkDeleteResponse>("/api/candidates/bulk-delete/", { method: "POST", body: { ids } });
}

export function listCandidateMessages(
  id: number,
  status?: MessageStatus,
  signal?: AbortSignal,
): Promise<Message[]> {
  return apiRequest<Message[]>(`/api/candidates/${id}/messages/`, { query: { status }, signal });
}
