"use client";

import { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { SideDrawer } from "@/components/common/SideDrawer";
import { useNotify } from "@/components/providers/NotificationProvider";
import { bulkSendMessage, sendMessage, toApiError } from "@/lib/api";
import { pluralize } from "@/lib/format";
import { BULK_MAX_RECIPIENTS, validateMessageBody } from "@/lib/validation";
import type { Candidate, Message } from "@/types";
import { FailedRecipients, toRecipientResult, type RecipientResult } from "./FailedRecipients";
import { MessageField } from "./MessageField";
import { RecipientChips } from "./RecipientChips";

interface SendMessageDrawerProps {
  open: boolean;
  recipients: Candidate[];
  onClose: () => void;
  /** Called whenever the backend recorded a message (sent, failed or retried). */
  onMessagesChanged: () => void;
}

export function SendMessageDrawer({ open, recipients, onClose, onMessagesChanged }: SendMessageDrawerProps) {
  const notify = useNotify();
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [failures, setFailures] = useState<RecipientResult[] | null>(null);

  const candidatesById = useMemo(() => new Map(recipients.map((c) => [c.id, c])), [recipients]);
  const recipientError =
    recipients.length > BULK_MAX_RECIPIENTS ? `You can message at most ${BULK_MAX_RECIPIENTS} candidates at once.` : null;
  const canSend = recipients.length > 0 && !recipientError && validateMessageBody(body) === null && !submitting;

  const reset = () => {
    setBody("");
    setSubmitError(null);
    setFailures(null);
  };

  const send = async () => {
    if (!canSend) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const text = body.trim();
      let failed: RecipientResult[];
      if (recipients.length === 1) {
        const message = await sendMessage({ candidate_id: recipients[0].id, body: text });
        failed = message.status === "failed" ? [toRecipientResult(message)] : [];
      } else {
        const response = await bulkSendMessage({ candidate_ids: recipients.map((c) => c.id), body: text });
        failed = response.results.filter((item) => item.status === "failed").map((item) => ({ ...item, attempt: 1 }));
      }
      onMessagesChanged();
      if (failed.length === 0) {
        notify(`Message sent to ${recipients.length === 1 ? recipients[0].name : pluralize(recipients.length, "candidate")}.`);
        onClose();
      } else {
        setFailures(failed);
      }
    } catch (error) {
      setSubmitError(toApiError(error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetried = (message: Message) => {
    setFailures((current) =>
      current?.map((result) => (result.candidate_id === message.candidate_id ? toRecipientResult(message) : result)) ?? null,
    );
    onMessagesChanged();
  };

  return (
    <SideDrawer
      open={open}
      title="Send Message"
      busy={submitting}
      onClose={onClose}
      onExited={reset}
      footer={
        failures ? (
          <Button variant="contained" onClick={onClose}>
            Done
          </Button>
        ) : (
          <>
            <Button variant="outlined" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => void send()}
              disabled={!canSend}
              startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : undefined}
            >
              Send Message
            </Button>
          </>
        )
      }
    >
      <Typography variant="body2" sx={{ mb: 1 }}>
        {pluralize(recipients.length, "Recipient")}
      </Typography>
      <RecipientChips recipients={recipients} />

      <Box sx={{ mt: 3.5 }}>
        {failures ? (
          <FailedRecipients
            results={failures}
            total={recipients.length}
            candidates={candidatesById}
            onRetried={handleRetried}
          />
        ) : (
          <>
            <MessageField value={body} onChange={setBody} disabled={submitting} />
            {recipientError ? (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {recipientError}
              </Alert>
            ) : null}
            {submitError ? (
              <Alert severity="error" sx={{ mt: 2 }} onClose={() => setSubmitError(null)}>
                {submitError}
              </Alert>
            ) : null}
          </>
        )}
      </Box>
    </SideDrawer>
  );
}
