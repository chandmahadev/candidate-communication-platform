"use client";

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { AppDialog } from "@/components/common/AppDialog";
import { useNotify } from "@/components/providers/NotificationProvider";
import { bulkDeleteCandidates, deleteCandidate, toApiError } from "@/lib/api";
import type { Candidate } from "@/types";

interface DeleteCandidatesDialogProps {
  open: boolean;
  candidates: Candidate[];
  onClose: () => void;
  onDeleted: (ids: number[]) => void;
}

export function DeleteCandidatesDialog({ open, candidates, onClose, onDeleted }: DeleteCandidatesDialogProps) {
  const notify = useNotify();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const count = candidates.length;
  const single = count === 1;

  const handleDelete = async () => {
    const ids = candidates.map((candidate) => candidate.id);
    setDeleting(true);
    setError(null);
    try {
      if (single) await deleteCandidate(ids[0]);
      else await bulkDeleteCandidates(ids);
      notify(single ? `${candidates[0].name} was deleted.` : `${count} candidates were deleted.`, "success");
      onDeleted(ids);
      onClose();
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AppDialog
      open={open}
      title="Delete Candidate"
      busy={deleting}
      onClose={onClose}
      onExited={() => setError(null)}
      actions={
        <>
          <Button variant="outlined" onClick={onClose} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => void handleDelete()}
            disabled={deleting || count === 0}
            startIcon={deleting ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {single ? "Delete Candidate" : `Delete ${count} Candidates`}
          </Button>
        </>
      }
    >
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      <Typography variant="body1">
        {single ? "Are you sure you want to delete this Candidate?" : `Are you sure you want to delete ${count} Candidates?`}
      </Typography>
      <Typography variant="caption" component="p" color="text.secondary" sx={{ mt: 0.5 }}>
        {single
          ? `This action cannot be undone, and you'll lose all communication history with ${candidates[0]?.name ?? "this candidate"}.`
          : "This action cannot be undone, and you'll lose all communication history with these candidates"}
      </Typography>
    </AppDialog>
  );
}
