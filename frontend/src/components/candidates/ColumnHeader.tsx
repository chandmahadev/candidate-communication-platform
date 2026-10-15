"use client";

import { useState, type ReactNode } from "react";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import IconButton from "@mui/material/IconButton";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TableCell from "@mui/material/TableCell";
import Tooltip from "@mui/material/Tooltip";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import FilterListIcon from "@mui/icons-material/FilterList";
import { STATUS_FILTER_OPTIONS, type SortDirection, type StatusFilterValue } from "@/lib/candidateTable";

function HeaderLayout({ label, control }: { label: string; control: ReactNode }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
      <span>{label}</span>
      {control}
    </Box>
  );
}

interface SortableHeaderProps {
  label: string;
  direction: SortDirection | null;
  onSort: () => void;
  width?: string | number;
}

export function SortableHeader({ label, direction, onSort, width }: SortableHeaderProps) {
  const Icon = direction === "asc" ? ArrowUpwardIcon : direction === "desc" ? ArrowDownwardIcon : FilterListIcon;
  const nextLabel = direction === "asc" ? "descending" : direction === "desc" ? "default order" : "ascending";
  return (
    <TableCell
      sx={{ width }}
      aria-sort={direction === "asc" ? "ascending" : direction === "desc" ? "descending" : undefined}
    >
      <HeaderLayout
        label={label}
        control={
          <Tooltip title={`Sort ${nextLabel}`}>
            <IconButton size="small" aria-label={`Sort by ${label}, ${nextLabel}`} onClick={onSort}>
              <Icon fontSize="small" sx={{ color: direction ? "primary.main" : "action.active" }} />
            </IconButton>
          </Tooltip>
        }
      />
    </TableCell>
  );
}

interface StatusFilterHeaderProps {
  selected: ReadonlySet<StatusFilterValue>;
  onChange: (next: Set<StatusFilterValue>) => void;
  width?: string | number;
}

export function StatusFilterHeader({ selected, onChange, width }: StatusFilterHeaderProps) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  const toggle = (value: StatusFilterValue) => {
    const next = new Set(selected);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange(next);
  };

  return (
    <TableCell sx={{ width }}>
      <HeaderLayout
        label="Status"
        control={
          <>
            <Tooltip title="Filter by status">
              <IconButton
                size="small"
                aria-label="Filter by status"
                aria-haspopup="menu"
                aria-expanded={anchor ? true : undefined}
                onClick={(event) => setAnchor(event.currentTarget)}
              >
                <Badge color="primary" variant="dot" invisible={selected.size === 0}>
                  <FilterListIcon fontSize="small" sx={{ color: selected.size ? "primary.main" : "action.active" }} />
                </Badge>
              </IconButton>
            </Tooltip>
            <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
              {STATUS_FILTER_OPTIONS.map((option) => (
                <MenuItem key={option.value} dense onClick={() => toggle(option.value)}>
                  <Checkbox size="small" edge="start" checked={selected.has(option.value)} tabIndex={-1} disableRipple />
                  <ListItemText primary={option.label} />
                </MenuItem>
              ))}
              <MenuItem dense disabled={selected.size === 0} onClick={() => onChange(new Set())} sx={{ color: "primary.main" }}>
                Clear filter
              </MenuItem>
            </Menu>
          </>
        }
      />
    </TableCell>
  );
}
