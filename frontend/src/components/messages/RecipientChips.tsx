"use client";

import { useLayoutEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import type { Candidate } from "@/types";

const MAX_LINES = 2;
const GAP_PX = 8;

const chipSx = { bgcolor: "rgba(0, 0, 0, 0.08)", fontSize: "0.8125rem" } as const;

/** Chips are measured in a hidden copy of the list so the visible one doesn't jump. */
export function RecipientChips({ recipients }: { recipients: Candidate[] }) {
  const measureRef = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(recipients.length);

  useLayoutEffect(() => {
    const container = measureRef.current;
    if (!container) return;

    const measure = () => {
      const chips = Array.from(container.querySelectorAll<HTMLElement>("[data-chip]"));
      const more = container.querySelector<HTMLElement>("[data-more]");
      const rowTops = [...new Set(chips.map((chip) => chip.offsetTop))].sort((a, b) => a - b);
      if (rowTops.length <= MAX_LINES || !more) {
        setVisibleCount(chips.length);
        return;
      }
      const lastRowTop = rowTops[MAX_LINES - 1];
      const width = container.clientWidth;
      let count = 0;
      for (const chip of chips) {
        if (chip.offsetTop < lastRowTop) count += 1;
        else if (chip.offsetTop === lastRowTop && chip.offsetLeft + chip.offsetWidth + GAP_PX + more.offsetWidth <= width)
          count += 1;
        else break;
      }
      setVisibleCount(Math.max(1, count));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, [recipients]);

  const hidden = recipients.slice(visibleCount);

  return (
    <Box sx={{ position: "relative" }}>
      <Box
        ref={measureRef}
        aria-hidden
        sx={{ position: "absolute", inset: 0, visibility: "hidden", pointerEvents: "none", display: "flex", flexWrap: "wrap", gap: 1 }}
      >
        {recipients.map((candidate) => (
          <Chip key={candidate.id} data-chip label={candidate.name} size="small" sx={chipSx} />
        ))}
        <Chip data-more label={`+ ${recipients.length}`} size="small" sx={{ ...chipSx, position: "absolute" }} />
      </Box>
      <Box component="ul" aria-label="Recipients" sx={{ display: "flex", flexWrap: "wrap", gap: 1, m: 0, p: 0, listStyle: "none" }}>
        {recipients.slice(0, visibleCount).map((candidate) => (
          <li key={candidate.id}>
            <Chip label={candidate.name} size="small" sx={chipSx} />
          </li>
        ))}
        {hidden.length ? (
          <li>
            <Tooltip title={hidden.map((candidate) => candidate.name).join(", ")}>
              <Chip
                label={`+ ${hidden.length}`}
                size="small"
                aria-label={`and ${hidden.length} more`}
                sx={{ ...chipSx, fontWeight: 700 }}
              />
            </Tooltip>
          </li>
        ) : null}
      </Box>
    </Box>
  );
}
