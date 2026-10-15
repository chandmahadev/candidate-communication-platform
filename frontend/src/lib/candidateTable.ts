import type { Candidate } from "@/types";

export type SortKey = "name" | "phone" | "last_message_at" | "code";
export type SortDirection = "asc" | "desc";

export interface SortState {
  key: SortKey;
  direction: SortDirection;
}

export type StatusFilterValue = "read" | "sent" | "failed" | "na";

export const STATUS_FILTER_OPTIONS: { value: StatusFilterValue; label: string }[] = [
  { value: "read", label: "Read" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
  { value: "na", label: "NA" },
];

/** "Sent" also covers messages that progressed to Delivered but have not been read yet. */
function statusFilterValue(candidate: Candidate): StatusFilterValue {
  switch (candidate.last_message_status) {
    case null:
      return "na";
    case "delivered":
      return "sent";
    default:
      return candidate.last_message_status;
  }
}

export function filterByStatus(candidates: Candidate[], statuses: ReadonlySet<StatusFilterValue>): Candidate[] {
  if (statuses.size === 0) return candidates;
  return candidates.filter((candidate) => statuses.has(statusFilterValue(candidate)));
}

const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });

function compare(a: Candidate, b: Candidate, key: SortKey): number {
  if (key === "last_message_at") {
    // Candidates without messages always sort last.
    if (!a.last_message_at || !b.last_message_at) return Number(!a.last_message_at) - Number(!b.last_message_at);
    return Date.parse(a.last_message_at) - Date.parse(b.last_message_at);
  }
  return collator.compare(a[key], b[key]);
}

/** Cycles a column through ascending → descending → unsorted. */
export function nextSort(current: SortState | null, key: SortKey): SortState | null {
  if (current?.key !== key) return { key, direction: "asc" };
  return current.direction === "asc" ? { key, direction: "desc" } : null;
}

export function sortCandidates(candidates: Candidate[], sort: SortState | null): Candidate[] {
  if (!sort) return candidates;
  const sign = sort.direction === "asc" ? 1 : -1;
  return [...candidates].sort((a, b) => {
    const result = compare(a, b, sort.key);
    if (sort.key === "last_message_at" && (!a.last_message_at || !b.last_message_at)) return result;
    return result * sign;
  });
}
