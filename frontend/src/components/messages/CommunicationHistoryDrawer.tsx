"use client";

import { useMemo } from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { SideDrawer } from "@/components/common/SideDrawer";
import { listCandidateMessages } from "@/lib/api";
import { formatPhone } from "@/lib/format";
import type { Candidate, Message } from "@/types";
import { useApiQuery } from "@/hooks/useApiQuery";
import { HistoryEntry } from "./HistoryEntry";

function newestFirst(messages: Message[]): Message[] {
  return [...messages].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id);
}

function HistoryList({ candidateId, onMessagesChanged }: { candidateId: number; onMessagesChanged: () => void }) {
  const query = useApiQuery(`candidate-messages:${candidateId}`, (signal) =>
    listCandidateMessages(candidateId, undefined, signal),
  );
  const messages = useMemo(() => newestFirst(query.data ?? []), [query.data]);

  const handleRetried = () => {
    query.reload();
    onMessagesChanged();
  };

  if (query.error) return <ErrorState error={query.error} title="Could not load communication history" onRetry={query.reload} />;
  if (!query.data) {
    return (
      <Stack spacing={2} sx={{ pt: 2.5 }} aria-label="Loading communication history">
        {[0, 1, 2].map((key) => (
          <Skeleton key={key} variant="rounded" height={88} />
        ))}
      </Stack>
    );
  }
  if (messages.length === 0) {
    return (
      <EmptyState
        title="No communication history"
        description="You have not communicated with this candidate yet. When you send them a message, it will appear here."
      />
    );
  }
  return (
    <Box component="ol" aria-label="Messages, newest first" sx={{ listStyle: "none", m: 0, p: 0 }}>
      {messages.map((message) => (
        <HistoryEntry key={message.id} message={message} onRetried={handleRetried} />
      ))}
    </Box>
  );
}

interface CommunicationHistoryDrawerProps {
  open: boolean;
  /** Kept after closing so the content does not disappear during the exit transition. */
  candidate: Candidate | null;
  onClose: () => void;
  onMessagesChanged: () => void;
}

export function CommunicationHistoryDrawer({ open, candidate, onClose, onMessagesChanged }: CommunicationHistoryDrawerProps) {
  return (
    <SideDrawer open={open} title="Communication history" onClose={onClose}>
      {candidate ? (
        <>
          <Box sx={{ pt: 2.5, pb: 2.5 }}>
            <Typography variant="caption" color="text.secondary">
              Candidate ID: {candidate.code}
            </Typography>
            <Typography variant="h5" component="p" sx={{ mt: 1, mb: 1, overflowWrap: "anywhere" }}>
              {candidate.name}
            </Typography>
            <Typography variant="body2">{formatPhone(candidate.phone)}</Typography>
            <Typography variant="body2" sx={{ mt: 1, overflowWrap: "anywhere" }}>
              {candidate.email}
            </Typography>
          </Box>
          <Divider />
          <HistoryList key={candidate.id} candidateId={candidate.id} onMessagesChanged={onMessagesChanged} />
        </>
      ) : null}
    </SideDrawer>
  );
}
