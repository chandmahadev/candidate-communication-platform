"use client";

import { useState, type MouseEvent } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import ReplayIcon from "@mui/icons-material/Replay";
import { retryMessage, toApiError, type ApiError } from "@/lib/api";
import type { Message } from "@/types";
import { useNotify } from "@/components/providers/NotificationProvider";

/** Retry rejections from the backend that will not change if the user tries again. */
const FINAL_REJECTION_CODES = new Set(["not_failed", "permanent_failure", "already_retried", "max_attempts_reached"]);

interface RetryMessageButtonProps {
  messageId: number;
  onRetried: (message: Message) => void;
  onError?: (error: ApiError) => void;
}

export function RetryMessageButton({ messageId, onRetried, onError }: RetryMessageButtonProps) {
  const notify = useNotify();
  const [pending, setPending] = useState(false);
  const [rejection, setRejection] = useState<string | null>(null);

  const handleClick = async (event: MouseEvent) => {
    event.stopPropagation();
    setPending(true);
    try {
      const message = await retryMessage(messageId);
      if (message.status === "failed") {
        notify(`Retry attempt ${message.attempt} failed: ${message.failure_reason}`, "warning");
      } else {
        notify(`Message re-sent to ${message.candidate_name}.`, "success");
      }
      onRetried(message);
    } catch (error) {
      const apiError = toApiError(error);
      if (apiError.code && FINAL_REJECTION_CODES.has(apiError.code)) setRejection(apiError.message);
      notify(`Retry failed: ${apiError.message}`, "error");
      onError?.(apiError);
    } finally {
      setPending(false);
    }
  };

  if (rejection) {
    return (
      <Tooltip title={rejection}>
        <Box component="span">
          <Button size="small" variant="outlined" disabled>
            Can&apos;t retry
          </Button>
        </Box>
      </Tooltip>
    );
  }

  return (
    <Button
      size="small"
      variant="outlined"
      color="error"
      onClick={handleClick}
      disabled={pending}
      startIcon={pending ? <CircularProgress size={14} color="inherit" /> : <ReplayIcon fontSize="small" />}
    >
      Retry
    </Button>
  );
}
