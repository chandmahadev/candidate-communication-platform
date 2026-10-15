"use client";

import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";
import { ErrorState } from "@/components/common/ErrorState";
import { STATUS_CONFIG } from "@/components/common/StatusChip";
import { getMessage } from "@/lib/api";
import { formatDate, formatTime } from "@/lib/format";
import type { MessageDetail, MessageStatus } from "@/types";
import { useApiQuery } from "@/hooks/useApiQuery";

type StepState = "done" | "pending" | "skipped";

interface ProgressStep {
  status: MessageStatus;
  title: string;
  state: StepState;
  at: string | null;
  note: string;
}

const PROGRESS_RANK: Record<Exclude<MessageStatus, "failed">, number> = { sent: 0, delivered: 1, read: 2 };

function lastEventAt(message: MessageDetail, status: MessageStatus): string | null {
  const events = message.status_events.filter((event) => event.new_status === status);
  return events.length ? events[events.length - 1].occurred_at : null;
}

/** Expected lifecycle: Sent → Delivered → Read, or Sent → Failed. */
function buildProgress(message: MessageDetail): ProgressStep[] {
  const accepted = message.provider_message_id !== null;
  const sentStep: ProgressStep = {
    status: "sent",
    title: accepted ? "Sent" : "Send attempted",
    state: accepted ? "done" : "skipped",
    at: message.sent_at ?? message.created_at,
    note: accepted ? STATUS_CONFIG.sent.description : "The provider did not accept the message",
  };

  if (message.status === "failed") {
    const steps: ProgressStep[] = [sentStep];
    const deliveredAt = lastEventAt(message, "delivered");
    if (deliveredAt) {
      steps.push({ status: "delivered", title: "Delivered", state: "done", at: deliveredAt, note: STATUS_CONFIG.delivered.description });
    }
    steps.push({
      status: "failed",
      title: "Failed",
      state: "done",
      at: lastEventAt(message, "failed") ?? message.updated_at,
      note: message.failure_reason || STATUS_CONFIG.failed.description,
    });
    return steps;
  }

  const currentRank = PROGRESS_RANK[message.status];
  return (["sent", "delivered", "read"] as const).map((status) => {
    if (status === "sent") return sentStep;
    const reached = currentRank >= PROGRESS_RANK[status];
    return {
      status,
      title: status === "read" ? "Read" : STATUS_CONFIG[status].label,
      state: reached ? "done" : "pending",
      at: reached ? lastEventAt(message, status) : null,
      note: reached ? STATUS_CONFIG[status].description : "Waiting for provider update",
    };
  });
}

function ProgressTimeline({ steps }: { steps: ProgressStep[] }) {
  return (
    <Box component="ol" sx={{ listStyle: "none", m: 0, p: 0 }} aria-label="Status timeline">
      {steps.map((step, index) => {
        const config = STATUS_CONFIG[step.status];
        const done = step.state === "done";
        const last = index === steps.length - 1;
        return (
          <Box component="li" key={step.status} sx={{ display: "flex", gap: 1.5 }}>
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", pt: 0.5 }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  bgcolor: done ? config.color : "transparent",
                  border: 2,
                  borderColor: done ? config.color : "divider",
                }}
              />
              {!last ? <Box sx={{ flex: 1, width: 2, my: 0.5, bgcolor: "divider" }} /> : null}
            </Box>
            <Box sx={{ pb: last ? 0 : 1.5, minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 700, color: done ? config.color : "text.disabled" }}>
                {step.title}
                {step.state === "pending" ? (
                  <Typography component="span" variant="caption" sx={{ ml: 1, color: "text.disabled" }}>
                    Pending
                  </Typography>
                ) : null}
              </Typography>
              <Typography variant="caption" color={done ? "text.secondary" : "text.disabled"} sx={{ display: "block" }}>
                {step.note}
                {done && step.at ? ` | ${formatDate(step.at)} ${formatTime(step.at)}` : ""}
              </Typography>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

/** Loads a message's status events and renders its progress timeline. */
export function MessageProgress({ messageId }: { messageId: number }) {
  const query = useApiQuery(`message:${messageId}`, (signal) => getMessage(messageId, signal));

  if (query.error) return <ErrorState error={query.error} title="Could not load status timeline" onRetry={query.reload} />;
  if (!query.data) return <Skeleton variant="rounded" height={88} />;

  const { attempt } = query.data;
  return (
    <Box>
      {attempt > 1 ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
          Attempt {attempt}
        </Typography>
      ) : null}
      <ProgressTimeline steps={buildProgress(query.data)} />
    </Box>
  );
}
