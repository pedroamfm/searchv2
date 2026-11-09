"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type RefObject } from "react";

import { ApiClientError, getApi, postApi } from "@/lib/api-client";

export type Job = {
  job_id: string;
  job_type: string;
  status: string;
  error_code: string | null;
};
type Operation = {
  id: string;
  jobType: "report" | "capture";
  scope: "full" | "daily_highlights" | "daily_catalog";
};
export type OperationState = "idle" | "running" | "success" | "error";
const terminal = (job?: Job) =>
  job?.status === "succeeded" || job?.status === "failed";
const rejected = (error: unknown) =>
  error instanceof ApiClientError &&
  error.status >= 400 &&
  error.status < 500 &&
  error.status !== 408;

export function useJobOperation(
  operation: Operation,
  captureLockRef?: RefObject<string | null>,
) {
  const client = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const requestLocked = useRef(false);
  const invalidated = useRef<string | null>(null);
  const mutation = useMutation({
    retry: false,
    mutationFn: async () => {
      const csrf = document.cookie
        .split("; ")
        .find((entry) => entry.startsWith("product_radar_csrf="))
        ?.split("=")[1];
      const job = await postApi<Job>(
        "/jobs",
        {
          job_type: operation.jobType,
          source_code: "mercado_libre",
          site_id: "MLC",
          scope: operation.scope,
        },
        csrf,
      );
      if (
        !job?.job_id ||
        !["queued", "running", "succeeded", "failed"].includes(job.status)
      )
        throw new Error("Unconfirmed job response");
      return job;
    },
    onSuccess: (job) => {
      setSubmitting(false);
      client.setQueryData(["job", job.job_id], job);
      setJobId(job.job_id);
      void client.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (error) => {
      setSubmitting(false);
      if (rejected(error)) {
        requestLocked.current = false;
        if (captureLockRef?.current === operation.id)
          captureLockRef.current = null;
      }
      void client.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const status = useQuery({
    queryKey: ["job", jobId],
    enabled: jobId !== null,
    queryFn: ({ signal }) =>
      getApi<Job>(`/jobs/${encodeURIComponent(jobId!)}`, { signal }),
    retry: false,
    staleTime: 0,
    refetchInterval: (query) =>
      terminal(query.state.data) || query.state.status === "error"
        ? false
        : 3000,
  });
  const job = status.data;
  useEffect(() => {
    if (!terminal(job)) return;
    requestLocked.current = false;
    if (captureLockRef?.current === operation.id) captureLockRef.current = null;
    if (job?.status === "succeeded" && invalidated.current !== job.job_id) {
      invalidated.current = job.job_id;
      for (const key of [
        "jobs",
        "dashboard-summary",
        "reports",
        "trends",
        "products",
        "product",
        "categories",
        "captures",
      ]) {
        void client.invalidateQueries({ queryKey: [key] });
      }
    }
  }, [captureLockRef, client, job, operation.id]);

  const uncertain = mutation.isError && !rejected(mutation.error);
  const checkingFailed = jobId !== null && status.isError && !terminal(job);
  const state: OperationState =
    submitting || mutation.isPending
      ? "running"
      : mutation.isError || checkingFailed || job?.status === "failed"
        ? "error"
        : job?.status === "succeeded"
          ? "success"
          : jobId
            ? "running"
            : "idle";
  const isLocked = state === "running" || uncertain || checkingFailed;

  function start() {
    // The ref closes the gap before React renders the disabled button.
    if (requestLocked.current || captureLockRef?.current) return;
    requestLocked.current = true;
    if (captureLockRef) captureLockRef.current = operation.id;
    setJobId(null);
    setSubmitting(true);
    mutation.mutate();
  }
  return {
    state,
    job,
    isLocked,
    uncertain,
    checkingFailed,
    submitting,
    start,
    checkStatus: () => status.refetch(),
    conflict:
      mutation.error instanceof ApiClientError &&
      mutation.error.code === "active_capture_exists",
  };
}
