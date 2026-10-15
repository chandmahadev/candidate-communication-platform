export const MESSAGE_STATUSES = ["sent", "delivered", "read", "failed"] as const;

export type MessageStatus = (typeof MESSAGE_STATUSES)[number];

export interface Message {
  id: number;
  candidate_id: number;
  candidate_name: string;
  body: string;
  status: MessageStatus;
  provider_message_id: string | null;
  error_code: string;
  failure_reason: string;
  is_retryable: boolean;
  attempt: number;
  retry_of_id: number | null;
  retried_by_id: number | null;
  created_at: string;
  sent_at: string | null;
  updated_at: string;
}

export interface MessageStatusEvent {
  id: number;
  provider_event_id: string;
  previous_status: MessageStatus;
  new_status: MessageStatus;
  occurred_at: string;
  received_at: string;
}

export interface MessageDetail extends Message {
  status_events: MessageStatusEvent[];
}

export interface SendMessageInput {
  candidate_id: number;
  body: string;
}

export interface BulkSendInput {
  candidate_ids: number[];
  body: string;
}

export interface BulkSendResultItem {
  candidate_id: number;
  message_id: number | null;
  status: MessageStatus;
  provider_message_id: string | null;
  error_code: string;
  failure_reason: string;
  is_retryable: boolean;
}

export interface BulkSendResponse {
  summary: {
    total: number;
    sent: number;
    failed: number;
  };
  results: BulkSendResultItem[];
}

export interface MessageFilters {
  status?: MessageStatus;
  candidate?: number;
}
