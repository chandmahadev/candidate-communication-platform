"use client";

import { useId, type ReactNode } from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";

interface SideDrawerProps {
  open: boolean;
  title: string;
  busy?: boolean;
  onClose: () => void;
  onExited?: () => void;
  footer?: ReactNode;
  children: ReactNode;
}

export function SideDrawer({ open, title, busy = false, onClose, onExited, footer, children }: SideDrawerProps) {
  const titleId = useId();
  const close = () => {
    if (!busy) onClose();
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={close}
      slotProps={{
        paper: {
          role: "dialog",
          "aria-labelledby": titleId,
          sx: { width: { xs: "100%", sm: 480, md: 560 }, display: "flex", flexDirection: "column" },
        },
        transition: { onExited },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", px: 3.5, pt: 3, pb: 2 }}>
        <Typography id={titleId} variant="h6" component="h2" sx={{ fontSize: "1.125rem" }}>
          {title}
        </Typography>
        <IconButton aria-label="Close" onClick={close} disabled={busy} edge="end">
          <CloseIcon />
        </IconButton>
      </Box>
      <Box sx={{ flex: 1, overflowY: "auto", px: 3.5, pb: 3 }}>{children}</Box>
      {footer ? (
        <>
          <Divider />
          <Box sx={{ display: "flex", justifyContent: "flex-end", flexWrap: "wrap", gap: 1, px: 3.5, py: 2 }}>{footer}</Box>
        </>
      ) : null}
    </Drawer>
  );
}
