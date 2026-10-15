"use client";

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import { NotAvailable, StatusChip } from "@/components/common/StatusChip";
import { formatDate, formatPhone } from "@/lib/format";
import type { SortKey, SortState, StatusFilterValue } from "@/lib/candidateTable";
import type { Candidate } from "@/types";
import { SortableHeader, StatusFilterHeader } from "./ColumnHeader";

/** Blank rows keep the grid visible below short lists, as in the design. */
const MIN_ROWS = 10;
const COLUMN_COUNT = 6;

interface CandidateTableProps {
  rows: Candidate[];
  loading: boolean;
  selectedIds: ReadonlySet<number>;
  onToggle: (candidate: Candidate) => void;
  onToggleAll: () => void;
  onOpenHistory: (candidate: Candidate) => void;
  sort: SortState | null;
  onSort: (key: SortKey) => void;
  statusFilter: ReadonlySet<StatusFilterValue>;
  onStatusFilterChange: (next: Set<StatusFilterValue>) => void;
  /** Rendered across the table body when there are no rows. */
  emptyContent: ReactNode;
}

export function CandidateTable({
  rows,
  loading,
  selectedIds,
  onToggle,
  onToggleAll,
  onOpenHistory,
  sort,
  onSort,
  statusFilter,
  onStatusFilterChange,
  emptyContent,
}: CandidateTableProps) {
  const selectedCount = rows.filter((row) => selectedIds.has(row.id)).length;
  const allSelected = rows.length > 0 && selectedCount === rows.length;
  const direction = (key: SortKey) => (sort?.key === key ? sort.direction : null);
  const fillerCount = rows.length ? Math.max(0, MIN_ROWS - rows.length) : 0;

  return (
    <Box sx={{ overflowX: "auto", position: "relative" }}>
      <Table size="small" sx={{ minWidth: 820, tableLayout: "fixed" }} aria-label="Candidates">
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox" sx={{ width: 52 }}>
              <Checkbox
                size="small"
                checked={allSelected}
                indeterminate={selectedCount > 0 && !allSelected}
                onChange={onToggleAll}
                disabled={rows.length === 0}
                slotProps={{ input: { "aria-label": allSelected ? "Deselect all candidates" : "Select all candidates" } }}
              />
            </TableCell>
            <SortableHeader label="Full name" direction={direction("name")} onSort={() => onSort("name")} width="19%" />
            <SortableHeader label="Mobile number" direction={direction("phone")} onSort={() => onSort("phone")} width="22%" />
            <SortableHeader
              label="Last message"
              direction={direction("last_message_at")}
              onSort={() => onSort("last_message_at")}
              width="22%"
            />
            <StatusFilterHeader selected={statusFilter} onChange={onStatusFilterChange} width="22%" />
            <SortableHeader label="Candidate ID" direction={direction("code")} onSort={() => onSort("code")} width="15%" />
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={COLUMN_COUNT} sx={{ borderBottom: 0 }}>
                {emptyContent}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((candidate) => {
              const selected = selectedIds.has(candidate.id);
              return (
                <TableRow key={candidate.id} hover selected={selected} sx={{ height: 44 }}>
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={selected}
                      onChange={() => onToggle(candidate)}
                      slotProps={{ input: { "aria-label": `Select ${candidate.name}` } }}
                    />
                  </TableCell>
                  <TableCell sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    <Link
                      component="button"
                      type="button"
                      underline="hover"
                      variant="body2"
                      onClick={() => onOpenHistory(candidate)}
                      title={`View communication history for ${candidate.name}`}
                      sx={{ maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", verticalAlign: "middle" }}
                    >
                      {candidate.name}
                    </Link>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{formatPhone(candidate.phone)}</TableCell>
                  <TableCell>{candidate.last_message_at ? formatDate(candidate.last_message_at) : <NotAvailable />}</TableCell>
                  <TableCell>
                    {candidate.last_message_status ? <StatusChip status={candidate.last_message_status} /> : <NotAvailable />}
                  </TableCell>
                  <TableCell sx={{ fontVariantNumeric: "tabular-nums" }}>{candidate.code}</TableCell>
                </TableRow>
              );
            })
          )}
          {Array.from({ length: fillerCount }, (_, index) => (
            <TableRow key={`filler-${index}`} aria-hidden sx={{ height: 44 }}>
              <TableCell colSpan={COLUMN_COUNT} />
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {loading ? (
        <LinearProgress sx={{ position: "absolute", top: 0, left: 0, right: 0, height: 2 }} aria-label="Loading candidates" />
      ) : null}
    </Box>
  );
}
