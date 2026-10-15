import type { Message } from "@/types";

/** A failed message can be retried once, and only if the backend marked the failure as temporary. */
export function canRetry(message: Pick<Message, "status" | "is_retryable" | "retried_by_id">): boolean {
  return message.status === "failed" && message.is_retryable && message.retried_by_id === null;
}

export function messageTimestamp(message: Pick<Message, "sent_at" | "created_at">): string {
  return message.sent_at ?? message.created_at;
}
