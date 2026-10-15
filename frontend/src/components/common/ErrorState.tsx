import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Button from "@mui/material/Button";
import type { ApiError } from "@/lib/api";

interface ErrorStateProps {
  error: ApiError;
  title?: string;
  onRetry?: () => void;
}

export function ErrorState({ error, title, onRetry }: ErrorStateProps) {
  return (
    <Alert
      severity="error"
      sx={{ my: 2 }}
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Try again
          </Button>
        ) : undefined
      }
    >
      <AlertTitle>{title ?? (error.isNetworkError ? "Connection problem" : "Something went wrong")}</AlertTitle>
      {error.message}
    </Alert>
  );
}
