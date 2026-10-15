"use client";

import { useId, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { STATUS_CONFIG, StatusChip } from "@/components/common/StatusChip";
import { formatDate, formatTime } from "@/lib/format";
import { canRetry, messageTimestamp } from "@/lib/messages";
import type { Message } from "@/types";
import { MessageProgress } from "./MessageProgress";
import { RetryMessageButton } from "./RetryMessageButton";

function failureHint(message: Message): string {
  if (message.retried_by_id !== null) return "Already retried — see the newer message above.";
  return message.is_retryable ? "" : "This failure is permanent and cannot be retried.";
}

interface HistoryEntryProps {
  message: Message;
  onRetried: () => void;
}

export function HistoryEntry({ message, onRetried }: HistoryEntryProps) {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  const timestamp = messageTimestamp(message);
  const failed = message.status === "failed";
  const hint = failed ? failureHint(message) : "";

  return (
    <Box component="li" sx={{ py: 2.5, borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, mb: 1.25 }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
          {formatDate(timestamp)}
          <Box component="span" sx={{ mx: 1 }} aria-hidden>
            |
          </Box>
          {formatTime(timestamp)}
        </Typography>
        <StatusChip status={message.status} />
      </Box>
      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {message.body}
      </Typography>

      {failed ? (
        <Box
          sx={{
            display: "flex",
            alignItems: { xs: "flex-start", sm: "center" },
            flexDirection: { xs: "column", sm: "row" },
            gap: 1.5,
            mt: 1.5,
            p: 1.5,
            borderRadius: 1,
            bgcolor: STATUS_CONFIG.failed.background,
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ color: "error.main" }}>
              {message.failure_reason || "Message could not be sent."}
            </Typography>
            {hint ? (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                {hint}
              </Typography>
            ) : null}
          </Box>
          {canRetry(message) ? <RetryMessageButton messageId={message.id} onRetried={onRetried} onError={onRetried} /> : null}
        </Box>
      ) : null}

      <Button
        size="small"
        onClick={() => setExpanded((value) => !value)}
        endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        aria-expanded={expanded}
        aria-controls={panelId}
        sx={{ mt: 1, ml: -0.75, textTransform: "none", fontWeight: 400 }}
      >
        {expanded ? "Hide status" : "View status"}
      </Button>
      <Collapse in={expanded} unmountOnExit>
        <Box id={panelId} sx={{ pt: 1.5 }}>
          <MessageProgress messageId={message.id} />
        </Box>
      </Collapse>
    </Box>
  );
}
