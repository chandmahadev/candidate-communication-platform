import type { ReactElement } from "react";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/Check";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import type { MessageStatus } from "@/types";

interface StatusConfig {
  label: string;
  color: string;
  background: string;
  icon?: ReactElement;
  description: string;
}

export const STATUS_CONFIG: Record<MessageStatus, StatusConfig> = {
  sent: {
    label: "Sent",
    color: "#1976D2",
    background: "#E3F2FD",
    description: "Accepted by the provider",
  },
  delivered: {
    label: "Delivered",
    color: "#00796B",
    background: "#E0F2F1",
    icon: <DoneAllIcon />,
    description: "Delivered to the candidate",
  },
  read: {
    label: "read",
    color: "#2E7D32",
    background: "#EDF7ED",
    icon: <CheckIcon />,
    description: "Read by the candidate",
  },
  failed: {
    label: "Failed",
    color: "#D32F2F",
    background: "#FDEDED",
    icon: <ErrorOutlineIcon />,
    description: "Could not be sent or delivered",
  },
};

export function StatusChip({ status }: { status: MessageStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <Chip
      size="small"
      icon={config.icon}
      label={config.label}
      title={config.description}
      sx={{
        height: 22,
        fontSize: "0.75rem",
        color: config.color,
        bgcolor: config.background,
        "& .MuiChip-label": { px: 1 },
        "& .MuiChip-icon": { color: config.color, fontSize: 14, ml: 0.75, mr: -0.5 },
      }}
    />
  );
}

/** Placeholder shown wherever a value does not exist yet. */
export function NotAvailable() {
  return (
    <Typography component="span" variant="body2" sx={{ color: "text.disabled" }}>
      NA
    </Typography>
  );
}
