"use client";

import { useId } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { MESSAGE_MAX_LENGTH } from "@/lib/validation";

interface MessageFieldProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  error?: string | null;
}

/** Resizable message textarea with the "n/1600" character counter. */
export function MessageField({ value, onChange, disabled = false, error }: MessageFieldProps) {
  const inputId = useId();
  const helperId = useId();
  const counterId = useId();
  const length = value.trim().length;
  const overLimit = length > MESSAGE_MAX_LENGTH;
  const invalid = overLimit || Boolean(error);

  return (
    <Box>
      <Typography component="label" htmlFor={inputId} variant="body1" sx={{ display: "block" }}>
        Message{" "}
        <Box component="span" sx={{ color: "error.main" }} aria-hidden>
          *
        </Box>
      </Typography>
      <Typography id={helperId} variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
        Type, or paste the message you want to send.
      </Typography>
      <Box
        component="textarea"
        id={inputId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Type or paste here..."
        disabled={disabled}
        required
        aria-invalid={invalid}
        aria-describedby={`${helperId} ${counterId}`}
        sx={{
          display: "block",
          width: "100%",
          minHeight: 134,
          maxHeight: "60vh",
          resize: "vertical",
          p: "12px",
          font: "inherit",
          fontSize: "0.875rem",
          lineHeight: 1.5,
          color: "text.primary",
          bgcolor: "background.paper",
          border: 1,
          borderColor: invalid ? "error.main" : "rgba(0, 0, 0, 0.23)",
          borderRadius: 1,
          outline: "none",
          "&::placeholder": { color: "text.disabled" },
          "&:hover:not(:disabled)": { borderColor: invalid ? "error.main" : "text.primary" },
          "&:focus": { borderColor: invalid ? "error.main" : "primary.main", boxShadow: (theme) => `inset 0 0 0 1px ${invalid ? theme.palette.error.main : theme.palette.primary.main}` },
          "&:disabled": { color: "text.disabled", bgcolor: "action.hover" },
        }}
      />
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, mt: 0.5 }}>
        <Typography variant="caption" sx={{ color: "error.main" }} role={error || overLimit ? "alert" : undefined}>
          {overLimit ? `Message must be at most ${MESSAGE_MAX_LENGTH} characters.` : (error ?? "")}
        </Typography>
        <Typography
          id={counterId}
          variant="caption"
          sx={{ color: overLimit ? "error.main" : "text.secondary", fontVariantNumeric: "tabular-nums", flexShrink: 0 }}
        >
          {length}/{MESSAGE_MAX_LENGTH}
        </Typography>
      </Box>
    </Box>
  );
}
