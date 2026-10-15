import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { EmptyIllustration } from "./EmptyIllustration";

interface EmptyStateProps {
  title: string;
  description: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Box
      role="status"
      sx={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", px: 3, py: 6 }}
    >
      <EmptyIllustration />
      <Typography variant="subtitle1" component="p" sx={{ mt: 3 }}>
        {title}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5, maxWidth: 320 }}>
        {description}
      </Typography>
      {action ? <Box sx={{ mt: 2 }}>{action}</Box> : null}
    </Box>
  );
}
