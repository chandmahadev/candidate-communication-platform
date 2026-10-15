import type {
  BulkSendInput,
  BulkSendResponse,
  Message,
  MessageDetail,
  MessageFilters,
  SendMessageInput,
} from "@/types";
import { apiRequest } from "./client";

export function listMessages(filters: MessageFilters = {}, signal?: AbortSignal): Promise<Message[]> {
  return apiRequest<Message[]>("/api/messages/", {
    query: { status: filters.status, candidate: filters.candidate },
    signal,
  });
}

export function getMessage(id: number, signal?: AbortSignal): Promise<MessageDetail> {
  return apiRequest<MessageDetail>(`/api/messages/${id}/`, { signal });
}

export function sendMessage(input: SendMessageInput): Promise<Message> {
  return apiRequest<Message>("/api/messages/send/", { method: "POST", body: input });
}

export function bulkSendMessage(input: BulkSendInput): Promise<BulkSendResponse> {
  return apiRequest<BulkSendResponse>("/api/messages/bulk-send/", { method: "POST", body: input });
}

export function retryMessage(id: number): Promise<Message> {
  return apiRequest<Message>(`/api/messages/${id}/retry/`, { method: "POST" });
}
