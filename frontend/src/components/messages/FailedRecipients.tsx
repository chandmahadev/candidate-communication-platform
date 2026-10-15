"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { StatusChip } from "@/components/common/StatusChip";
import { formatPhone } from "@/lib/format";
import type { BulkSendResultItem, Candidate, Message } from "@/types";
import { RetryMessageButton } from "./RetryMessageButton";

export interface RecipientResult extends BulkSendResultItem {
  attempt: number;
}

export function toRecipientResult(message: Message): RecipientResult {
  return {
    candidate_id: message.candidate_id,
    message_id: message.id,
    status: message.status,
    provider_message_id: message.provider_message_id,
    error_code: message.error_code,
    failure_reason: message.failure_reason,
    is_retryable: message.is_retryable,
    attempt: message.attempt,
  };
}

interface FailedRecipientsProps {
  /** Initial failures, updated in place as they are retried. */
  results: RecipientResult[];
  total: number;
  candidates: Map<number, Candidate>;
  onRetried: (message: Message) => void;
}

export function FailedRecipients({ results, total, candidates, onRetried }: FailedRecipientsProps) {
  const stillFailing = results.filter((result) => result.status === "failed").length;
  const sent = total - stillFailing;

  return (
    <Box>
      <Alert severity={stillFailing ? "error" : "success"} sx={{ mb: 2 }}>
        {stillFailing
          ? `Sent to ${sent} of ${total} ${total === 1 ? "recipient" : "recipients"}. ${stillFailing} could not be sent.`
          : `All messages were sent.`}
      </Alert>
      <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
        Failed recipients
      </Typography>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {results.map((result) => {
          const candidate = candidates.get(result.candidate_id);
          const failed = result.status === "failed";
          const retryable = failed && result.is_retryable && result.message_id !== null;
          return (
            <Box
              component="li"
              key={result.candidate_id}
              sx={{ display: "flex", alignItems: "flex-start", gap: 2, py: 1.5, borderBottom: 1, borderColor: "divider" }}
            >
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
                  {candidate?.name ?? `Candidate #${result.candidate_id}`}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  {candidate ? formatPhone(candidate.phone) : ""}
                  {result.attempt > 1 ? ` | Attempt ${result.attempt}` : ""}
                </Typography>
                {failed ? (
                  <Typography variant="caption" sx={{ display: "block", color: "error.main", mt: 0.25 }}>
                    {result.failure_reason || "Message could not be sent."}
                    {result.is_retryable ? "" : " This failure is permanent and cannot be retried."}
                  </Typography>
                ) : null}
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
                <StatusChip status={result.status} />
                {retryable && result.message_id !== null ? (
                  <RetryMessageButton messageId={result.message_id} onRetried={onRetried} />
                ) : null}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
