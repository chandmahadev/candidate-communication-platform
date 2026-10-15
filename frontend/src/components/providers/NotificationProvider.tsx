"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import Alert, { type AlertColor } from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";

interface Notification {
  id: number;
  message: string;
  severity: AlertColor;
}

type Notify = (message: string, severity?: AlertColor) => void;

const NotificationContext = createContext<Notify | null>(null);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [queue, setQueue] = useState<Notification[]>([]);
  const [open, setOpen] = useState(true);
  const current = queue[0];

  const notify = useCallback<Notify>((message, severity = "success") => {
    setQueue((items) => [...items, { id: Date.now() + Math.random(), message, severity }]);
    setOpen(true);
  }, []);

  const handleClose = (_event?: unknown, reason?: string) => {
    if (reason === "clickaway") return;
    setOpen(false);
  };

  const handleExited = () => {
    setQueue((items) => items.slice(1));
    setOpen(true);
  };

  return (
    <NotificationContext.Provider value={notify}>
      {children}
      <Snackbar
        key={current?.id}
        open={Boolean(current) && open}
        autoHideDuration={current?.severity === "error" ? 7000 : 4000}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        slotProps={{ transition: { onExited: handleExited } }}
      >
        {current ? (
          <Alert onClose={handleClose} severity={current.severity} variant="filled" sx={{ width: "100%" }}>
            {current.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </NotificationContext.Provider>
  );
}

export function useNotify(): Notify {
  const notify = useContext(NotificationContext);
  if (!notify) throw new Error("useNotify must be used within NotificationProvider");
  return notify;
}
