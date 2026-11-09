"use client";

import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";

import { useCurrentUser } from "@/components/auth-gate";
import { OperationCard } from "@/components/operation-card";
import { WorkspacePage } from "@/components/page-template";
import { Card, ErrorState, Skeleton } from "@/components/ui";
import { ApiClientError, getApi } from "@/lib/api-client";
import { useJobOperation, type Job } from "@/lib/use-job-operation";

type Summary = {
  latest_capture_at_utc: string | null;
  capture_count: number;
  raw_file_count: number;
  trend_count: number;
  product_count: number;
  covered_categories: number;
  freshness_at_utc: string | null;
};
const number = new Intl.NumberFormat("es-CL");

export default function Home() {
  const user = useCurrentUser();
  const captureLock = useRef<string | null>(null);
  const report = useJobOperation({
    id: "weekly",
    jobType: "report",
    scope: "full",
  });
  const rankings = useJobOperation(
    { id: "rankings", jobType: "capture", scope: "daily_highlights" },
    captureLock,
  );
  const catalog = useJobOperation(
    { id: "catalog", jobType: "capture", scope: "daily_catalog" },
    captureLock,
  );
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: ({ signal }) => getApi<{ items: Job[] }>("/jobs", { signal }),
    refetchInterval: (query) =>
      query.state.data?.items.some(
        (job) =>
          job.job_type === "capture" &&
          ["queued", "running"].includes(job.status),
      )
        ? 3000
        : false,
  });
  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: ({ signal }) => getApi<Summary>("/dashboard/summary", { signal }),
  });
  if (summary.isPending)
    return (
      <WorkspacePage
        eyebrow="Dashboard"
        title="Estado del radar"
        description="Cargando la evidencia disponible."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </WorkspacePage>
    );
  if (summary.isError)
    return (
      <WorkspacePage
        eyebrow="Dashboard"
        title="Estado del radar"
        description="Datos operacionales y cobertura."
      >
        <ErrorState
          message={
            summary.error instanceof ApiClientError
              ? summary.error.message
              : "No fue posible cargar el dashboard."
          }
        />
      </WorkspacePage>
    );
  const cards = [
    {
      label: "Tendencias",
      value: summary.data.trend_count,
      context:
        "Observaciones acumuladas; un término puede aparecer en varias capturas.",
    },
    {
      label: "Productos",
      value: summary.data.product_count,
      context:
        "Registros acumulados; un producto puede aparecer en varias capturas.",
    },
    {
      label: "Categorías cubiertas",
      value: summary.data.covered_categories,
      context:
        "Categorías distintas con tendencias observadas. El informe consulta 32 categorías.",
    },
    {
      label: "Evidencias originales",
      value: summary.data.raw_file_count,
      context: "Archivos RAW registrados en el historial.",
    },
  ];
  const activeCapture = jobs.data?.items.some(
    (job) =>
      job.job_type === "capture" && ["queued", "running"].includes(job.status),
  );
  const captureReason = jobs.isPending
    ? "Consultando si hay una captura activa."
    : jobs.isError
      ? "No se pudo verificar si hay capturas activas. Consulta el historial de trabajos."
      : activeCapture
        ? "Hay una captura en curso; las actualizaciones diarias estarán disponibles cuando termine."
        : undefined;
  const admin = user.data?.role === "admin";
  const reference = summary.data.freshness_at_utc;
  return (
    <WorkspacePage
      eyebrow="Dashboard"
      title="Estado del radar"
      description="Resumen acumulado de la evidencia registrada en el radar."
    >
      <p className="mb-4 text-sm text-[var(--muted)]">
        {reference ? (
          <>
            Última evidencia registrada:{" "}
            <time dateTime={reference}>
              {new Date(reference).toLocaleString("es-CL")}
            </time>
            .
          </>
        ) : (
          "Aún no hay una fecha de evidencia disponible."
        )}
        {summary.data.latest_capture_at_utc ? (
          <>
            {" "}
            Última captura finalizada:{" "}
            <time dateTime={summary.data.latest_capture_at_utc}>
              {new Date(summary.data.latest_capture_at_utc).toLocaleString(
                "es-CL",
              )}
            </time>
            .
          </>
        ) : null}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.label}>
            <p className="text-sm text-[var(--muted)]">{card.label}</p>
            <p className="mt-3 text-3xl font-semibold">
              {number.format(card.value)}
            </p>
            <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
              {card.context}
            </p>
          </Card>
        ))}
      </div>
      <div className="mt-5 grid items-stretch gap-5 lg:grid-cols-3">
        <OperationCard
          title="Informe semanal de 32 categorías"
          description="Captura completa: tendencias semanales, rankings, catálogo y visitas. Úsalo una vez por semana."
          action="Generar informe semanal"
          loadingLabel="Generando informe…"
          successLabel="Informe generado."
          reportsHref="/reports/informe-semanal"
          operation={report}
          primary
          admin={admin}
        />
        <OperationCard
          title="Rankings diarios"
          description="Actualiza los rankings de las 32 categorías y genera su informe diario. No consulta tendencias semanales."
          action="Actualizar rankings"
          loadingLabel="Actualizando rankings…"
          successLabel="Rankings actualizados e informe generado."
          reportsHref="/reports/ranking-diario"
          operation={rankings}
          admin={admin}
          disabledReason={
            catalog.isLocked
              ? "La actualización del catálogo está pendiente; espera a que termine."
              : captureReason
          }
        />
        <OperationCard
          title="Catálogo y visitas diarios"
          description="Actualiza una muestra de 12 productos y genera su informe diario de ofertas, precios y visitas."
          action="Actualizar catálogo"
          loadingLabel="Actualizando catálogo…"
          successLabel="Catálogo actualizado e informe generado."
          reportsHref="/reports/catalogo-diario"
          operation={catalog}
          admin={admin}
          disabledReason={
            rankings.isLocked
              ? "La actualización de rankings está pendiente; espera a que termine."
              : captureReason
          }
        />
      </div>
    </WorkspacePage>
  );
}
