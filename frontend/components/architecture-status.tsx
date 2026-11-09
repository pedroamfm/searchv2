"use client";

import { useQuery } from "@tanstack/react-query";

import { ApiClientError, getApi } from "@/lib/api-client";

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

async function getApiHealth(): Promise<HealthResponse> {
  return getApi<HealthResponse>("/health/live", { cache: "no-store" });
}

export function ArchitectureStatus() {
  const health = useQuery({ queryKey: ["api-health"], queryFn: getApiHealth });
  const online = health.data?.status === "ok";

  const message = health.isError
    ? health.error instanceof ApiClientError
      ? `Error ${health.error.code}`
      : "API no disponible"
    : online
      ? "Sistema conectado"
      : "Verificando API";

  return (
    <div aria-live="polite" className="flex min-w-48 items-center gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3">
      <span
        className={`h-2.5 w-2.5 rounded-full ${online ? "bg-[var(--accent)]" : "bg-amber-400"}`}
        aria-hidden="true"
      />
      <div>
        <p className="text-sm font-medium">{message}</p>
        <p className="text-xs text-[var(--muted)]">Next.js → FastAPI</p>
      </div>
    </div>
  );
}
