"use client";

import { useId, type FormEventHandler, type ReactNode } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import { useIsMobile } from "@/hooks/useIsMobile";

interface AppDialogProps {
  open: boolean;
  title: string;
  /** Prevents closing (backdrop, Escape and the X button) while a request is in flight. */
  busy?: boolean;
  onClose: () => void;
  onExited?: () => void;
  onSubmit?: FormEventHandler<HTMLFormElement>;
  actions: ReactNode;
  children: ReactNode;
}

export function AppDialog({ open, title, busy = false, onClose, onExited, onSubmit, actions, children }: AppDialogProps) {
  const titleId = useId();
  const isMobile = useIsMobile();
  const close = () => {
    if (!busy) onClose();
  };

  const body = (
    <>
      <DialogTitle
        id={titleId}
        sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", px: 3, pt: 3, pb: 1.5 }}
      >
        <Box component="span" sx={{ fontWeight: 700, fontSize: "1.125rem" }}>
          {title}
        </Box>
        <IconButton aria-label="Close" onClick={close} disabled={busy} edge="end">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ px: 3, pb: 4 }}>{children}</DialogContent>
      <Divider />
      <DialogActions sx={{ px: 3, py: 2.5, gap: 1 }}>{actions}</DialogActions>
    </>
  );

  return (
    <Dialog
      open={open}
      onClose={close}
      fullWidth
      maxWidth="sm"
      fullScreen={isMobile}
      aria-labelledby={titleId}
      slotProps={{ transition: { onExited }, paper: { sx: { maxWidth: { sm: 400 } } } }}
    >
      {onSubmit ? (
        <Box component="form" onSubmit={onSubmit} noValidate sx={{ display: "contents" }}>
          {body}
        </Box>
      ) : (
        body
      )}
    </Dialog>
  );
}
