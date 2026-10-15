"use client";

import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { CommunicationHistoryDrawer } from "@/components/messages/CommunicationHistoryDrawer";
import { SendMessageDrawer } from "@/components/messages/SendMessageDrawer";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { listCandidates } from "@/lib/api";
import {
  filterByStatus,
  nextSort,
  sortCandidates,
  type SortKey,
  type SortState,
  type StatusFilterValue,
} from "@/lib/candidateTable";
import type { Candidate } from "@/types";
import { AddCandidateDialog } from "./AddCandidateDialog";
import { CandidateTable } from "./CandidateTable";
import { CandidateToolbar } from "./CandidateToolbar";
import { DeleteCandidatesDialog } from "./DeleteCandidatesDialog";

export function CandidateCommunicationPage() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [sort, setSort] = useState<SortState | null>(null);
  const [statusFilter, setStatusFilter] = useState<Set<StatusFilterValue>>(new Set());

  const [addOpen, setAddOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTargets, setDeleteTargets] = useState<Candidate[]>([]);
  const [sendOpen, setSendOpen] = useState(false);
  const [recipients, setRecipients] = useState<Candidate[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyCandidate, setHistoryCandidate] = useState<Candidate | null>(null);

  const query = useApiQuery(`candidates:${debouncedSearch}`, (signal) => listCandidates(debouncedSearch, signal));
  const candidates = useMemo(() => query.data ?? [], [query.data]);
  const rows = useMemo(
    () => sortCandidates(filterByStatus(candidates, statusFilter), sort),
    [candidates, statusFilter, sort],
  );
  // Actions only ever apply to rows the user can currently see.
  const selectedRows = useMemo(() => rows.filter((row) => selectedIds.has(row.id)), [rows, selectedIds]);

  const searching = search.trim() !== debouncedSearch || (query.loading && Boolean(debouncedSearch));
  const filtering = Boolean(debouncedSearch) || statusFilter.size > 0;

  const toggle = (candidate: Candidate) =>
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(candidate.id)) next.delete(candidate.id);
      else next.add(candidate.id);
      return next;
    });

  const toggleAll = () =>
    setSelectedIds(selectedRows.length === rows.length ? new Set() : new Set(rows.map((row) => row.id)));

  const openDelete = () => {
    setDeleteTargets(selectedRows);
    setDeleteOpen(true);
  };

  const openSend = () => {
    setRecipients(selectedRows);
    setSendOpen(true);
  };

  const openHistory = (candidate: Candidate) => {
    setHistoryCandidate(candidate);
    setHistoryOpen(true);
  };

  const handleDeleted = (ids: number[]) => {
    setSelectedIds((current) => new Set([...current].filter((id) => !ids.includes(id))));
    query.reload();
  };

  const clearFilters = () => {
    setSearch("");
    setStatusFilter(new Set());
  };

  const emptyContent = query.error ? (
    <ErrorState error={query.error} title="Could not load candidates" onRetry={query.reload} />
  ) : !query.data ? null : filtering ? (
    <EmptyState
      title="No matching candidates"
      description={
        debouncedSearch ? `No candidates match “${debouncedSearch}”.` : "No candidates match the selected status."
      }
      action={
        <Button variant="outlined" onClick={clearFilters}>
          Clear filters
        </Button>
      }
    />
  ) : (
    <EmptyState title="No candidates added" description="When you add a candidate, they will appear here." />
  );

  return (
    <Box component="main" sx={{ minHeight: "100vh", bgcolor: "background.paper" }}>
      <Box
        component="header"
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          alignItems: { xs: "stretch", md: "center" },
          justifyContent: "space-between",
          gap: 2,
          px: { xs: 2, sm: 3 },
          py: 2,
        }}
      >
        <Typography variant="h5" component="h1" sx={{ whiteSpace: "nowrap" }}>
          Candidate communication
        </Typography>
        <CandidateToolbar
          selectedCount={selectedRows.length}
          search={search}
          searching={searching}
          onSearchChange={setSearch}
          onAdd={() => setAddOpen(true)}
          onDelete={openDelete}
          onSend={openSend}
        />
      </Box>
      <Box sx={{ height: 8, bgcolor: "#F5F5F5" }} />

      <CandidateTable
        rows={query.error ? [] : rows}
        loading={query.loading}
        selectedIds={selectedIds}
        onToggle={toggle}
        onToggleAll={toggleAll}
        onOpenHistory={openHistory}
        sort={sort}
        onSort={(key: SortKey) => setSort((current) => nextSort(current, key))}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        emptyContent={emptyContent}
      />

      <AddCandidateDialog open={addOpen} onClose={() => setAddOpen(false)} onCreated={query.reload} />
      <DeleteCandidatesDialog
        open={deleteOpen}
        candidates={deleteTargets}
        onClose={() => setDeleteOpen(false)}
        onDeleted={handleDeleted}
      />
      <SendMessageDrawer
        open={sendOpen}
        recipients={recipients}
        onClose={() => setSendOpen(false)}
        onMessagesChanged={query.reload}
      />
      <CommunicationHistoryDrawer
        open={historyOpen}
        candidate={historyCandidate}
        onClose={() => setHistoryOpen(false)}
        onMessagesChanged={query.reload}
      />
    </Box>
  );
}
