"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import AddIcon from "@mui/icons-material/Add";
import ClearIcon from "@mui/icons-material/Clear";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import SendIcon from "@mui/icons-material/Send";

interface CandidateToolbarProps {
  selectedCount: number;
  search: string;
  searching: boolean;
  onSearchChange: (value: string) => void;
  onAdd: () => void;
  onDelete: () => void;
  onSend: () => void;
}

export function CandidateToolbar({
  selectedCount,
  search,
  searching,
  onSearchChange,
  onAdd,
  onDelete,
  onSend,
}: CandidateToolbarProps) {
  const nothingSelected = selectedCount === 0;
  return (
    <Box
      role="toolbar"
      aria-label="Candidate actions"
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, justifyContent: { md: "flex-end" } }}
    >
      <Button variant="outlined" startIcon={<AddIcon />} onClick={onAdd}>
        Add Candidate
      </Button>
      <Button variant="contained" startIcon={<DeleteIcon />} onClick={onDelete} disabled={nothingSelected}>
        Delete Candidate
      </Button>
      <Button variant="contained" startIcon={<SendIcon />} onClick={onSend} disabled={nothingSelected}>
        Send Message
      </Button>
      <TextField
        size="small"
        placeholder="Search"
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        sx={{ width: { xs: "100%", sm: 200, lg: 240 } }}
        slotProps={{
          htmlInput: { "aria-label": "Search candidates" },
          input: {
            startAdornment: (
              <InputAdornment position="start">
                {searching ? <CircularProgress size={16} aria-label="Searching" /> : <SearchIcon fontSize="small" />}
              </InputAdornment>
            ),
            endAdornment: search ? (
              <InputAdornment position="end">
                <IconButton size="small" edge="end" aria-label="Clear search" onClick={() => onSearchChange("")}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : undefined,
          },
        }}
      />
    </Box>
  );
}
