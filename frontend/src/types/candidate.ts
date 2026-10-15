import type { MessageStatus } from "./message";

export interface Candidate {
  id: number;
  /** Public 6-character identifier shown in the UI, e.g. "A1B2C3". */
  code: string;
  name: string;
  email: string;
  phone: string;
  last_message_at: string | null;
  last_message_status: MessageStatus | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateInput {
  name: string;
  email: string;
  phone: string;
}

export interface BulkDeleteResponse {
  deleted: number;
}
