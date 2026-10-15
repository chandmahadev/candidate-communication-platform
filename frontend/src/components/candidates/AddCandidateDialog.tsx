"use client";

import { useState, type FormEvent } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { AppDialog } from "@/components/common/AppDialog";
import { useNotify } from "@/components/providers/NotificationProvider";
import { createCandidate, toApiError } from "@/lib/api";
import { validateCandidate, type CandidateFormErrors } from "@/lib/validation";
import type { Candidate, CandidateInput } from "@/types";

const EMPTY_FORM: CandidateInput = { name: "", email: "", phone: "" };
const FIELDS: (keyof CandidateInput)[] = ["name", "phone", "email"];

interface AddCandidateDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (candidate: Candidate) => void;
}

export function AddCandidateDialog({ open, onClose, onCreated }: AddCandidateDialogProps) {
  const notify = useNotify();
  const [form, setForm] = useState<CandidateInput>(EMPTY_FORM);
  const [errors, setErrors] = useState<CandidateFormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const complete = FIELDS.every((field) => form[field].trim() !== "");

  const reset = () => {
    setForm(EMPTY_FORM);
    setErrors({});
    setFormError(null);
  };

  const update = (field: keyof CandidateInput, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const validation = validateCandidate(form);
    setErrors(validation);
    setFormError(null);
    if (Object.keys(validation).length) return;

    setSubmitting(true);
    try {
      const candidate = await createCandidate({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
      });
      notify(`${candidate.name} was added.`, "success");
      onCreated(candidate);
      onClose();
    } catch (error) {
      const apiError = toApiError(error);
      const fieldErrors: CandidateFormErrors = {};
      for (const field of FIELDS) {
        const messages = apiError.fieldErrors[field];
        if (messages?.length) fieldErrors[field] = messages.join(" ");
      }
      setErrors(fieldErrors);
      const nonField = apiError.fieldErrors.non_field_errors?.join(" ");
      setFormError(nonField ?? (Object.keys(fieldErrors).length ? null : apiError.message));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppDialog
      open={open}
      title="Add Candidate"
      busy={submitting}
      onClose={onClose}
      onExited={reset}
      onSubmit={handleSubmit}
      actions={
        <>
          <Button variant="outlined" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!complete || submitting}
            startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            Add Candidate
          </Button>
        </>
      }
    >
      <Stack spacing={2.5} sx={{ pt: 1 }}>
        {formError ? <Alert severity="error">{formError}</Alert> : null}
        <TextField
          label="Candidate Name"
          value={form.name}
          onChange={(event) => update("name", event.target.value)}
          error={Boolean(errors.name)}
          helperText={errors.name}
          required
          autoFocus
          fullWidth
          disabled={submitting}
          slotProps={{ htmlInput: { maxLength: 255 } }}
        />
        <TextField
          label="Mobile Number"
          type="tel"
          autoComplete="off"
          value={form.phone}
          onChange={(event) => update("phone", event.target.value)}
          error={Boolean(errors.phone)}
          helperText={errors.phone}
          required
          fullWidth
          disabled={submitting}
          slotProps={{ htmlInput: { maxLength: 20 } }}
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="off"
          value={form.email}
          onChange={(event) => update("email", event.target.value)}
          error={Boolean(errors.email)}
          helperText={errors.email}
          required
          fullWidth
          disabled={submitting}
          slotProps={{ htmlInput: { maxLength: 254 } }}
        />
      </Stack>
    </AppDialog>
  );
}
