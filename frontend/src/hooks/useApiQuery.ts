"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, isAbortError, toApiError } from "@/lib/api";

interface QueryState<T> {
  requestId: string;
  data?: T;
  error?: ApiError;
}

export interface ApiQueryResult<T> {
  /** Latest successfully loaded data (kept while a new request is in flight). */
  data: T | undefined;
  error: ApiError | undefined;
  /** True while the request for the current key has not settled yet. */
  loading: boolean;
  reload: () => void;
  /** Replaces the cached data locally, e.g. after a mutation. */
  setData: (updater: (current: T | undefined) => T | undefined) => void;
}

/**
 * Fetches data for `key`, refetching whenever `key` changes or `reload()` is called.
 * Stale responses are aborted so that only the latest request updates the state.
 */
export function useApiQuery<T>(key: string, fetcher: (signal: AbortSignal) => Promise<T>): ApiQueryResult<T> {
  const fetcherRef = useRef(fetcher);
  const [reloadCount, setReloadCount] = useState(0);
  const [state, setState] = useState<QueryState<T>>({ requestId: "" });
  const requestId = `${key}#${reloadCount}`;

  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    const controller = new AbortController();
    fetcherRef.current(controller.signal).then(
      (data) => setState({ requestId, data }),
      (error: unknown) => {
        if (isAbortError(error)) return;
        setState((previous) => ({ requestId, data: previous.data, error: toApiError(error) }));
      },
    );
    return () => controller.abort();
  }, [requestId]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);
  const setData = useCallback(
    (updater: (current: T | undefined) => T | undefined) =>
      setState((previous) => ({ ...previous, data: updater(previous.data) })),
    [],
  );

  return {
    data: state.data,
    error: state.requestId === requestId ? state.error : undefined,
    loading: state.requestId !== requestId,
    reload,
    setData,
  };
}
