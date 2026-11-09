"use client";

import { useQuery } from "@tanstack/react-query";

import {
  Badge,
  ButtonLink,
  Card,
  DocumentLink,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { getApi } from "@/lib/api-client";
import { formatFileSize, reportFileDate } from "@/lib/report-format";

type Report = { filename: string; size_bytes: number; modified_at_utc: string };
export type ReportGroup = "catalog" | "rankings" | "weekly";

const documentTitles = {
  catalog: "Informe diario de catálogo",
  rankings: "Informe diario de rankings",
  weekly: "Informe semanal",
};

export const reportGroups: Record<
  ReportGroup,
  { title: string; description: string; href: string; emptyMessage: string }
> = {
  catalog: {
    title: "Catálogo Diario",
    description:
      "Productos priorizados, ofertas, precios y visitas observadas durante la actualización diaria.",
    href: "/reports/catalogo-diario",
    emptyMessage: "Aún no hay informes diarios de catálogo.",
  },
  rankings: {
    title: "Ranking Diario",
    description:
      "Posiciones, resultados y primeros lugares observados por categoría en cada captura diaria.",
    href: "/reports/ranking-diario",
    emptyMessage: "Aún no hay informes diarios de ranking.",
  },
  weekly: {
    title: "Informe Semanal",
    description:
      "Captura completa de las 32 categorías: tendencias, rankings, catálogo y visitas.",
    href: "/reports/informe-semanal",
    emptyMessage: "Aún no hay informes semanales disponibles.",
  },
};

function groupForReport(filename: string): ReportGroup | null {
  if (filename.includes("daily_catalog")) return "catalog";
  if (filename.includes("daily_rankings")) return "rankings";
  if (
    filename.includes("_sellers") ||
    filename.includes("_expanded_visits") ||
    filename.includes("_keyword_supply") ||
    filename.includes("_shipping")
  )
    return null;
  return "weekly";
}

function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: ({ signal }) =>
      getApi<{ items: Report[] }>("/reports", { signal }),
  });
}

export function ReportsIndex() {
  const reports = useReports();

  if (reports.isPending) return <Skeleton className="h-72" />;
  if (reports.isError)
    return <ErrorState message="No fue posible cargar los informes." />;

  const totals: Record<ReportGroup, number> = {
    catalog: 0,
    rankings: 0,
    weekly: 0,
  };
  reports.data.items.forEach((report) => {
    const group = groupForReport(report.filename);
    if (group) totals[group] += 1;
  });

  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {(
        Object.entries(reportGroups) as Array<
          [ReportGroup, (typeof reportGroups)[ReportGroup]]
        >
      ).map(([group, definition]) => (
        <Card className="flex min-h-64 flex-col" key={group}>
          <div>
            <p className="text-sm font-medium text-[var(--accent)]">
              {totals[group]} {totals[group] === 1 ? "documento" : "documentos"}
            </p>
            <h2 className="mt-3 text-xl font-semibold">{definition.title}</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              {definition.description}
            </p>
          </div>
          <div className="mt-auto pt-6">
            <ButtonLink variant="ghost" size="sm" href={definition.href}>
              Ver{" "}
              {group === "weekly"
                ? "informes semanales"
                : group === "rankings"
                  ? "informes de rankings"
                  : "informes de catálogo"}
            </ButtonLink>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function ReportGroupDocuments({
  group,
}: Readonly<{ group: ReportGroup }>) {
  const reports = useReports();
  const definition = reportGroups[group];

  if (reports.isPending) return <Skeleton className="h-72" />;
  if (reports.isError)
    return <ErrorState message="No fue posible cargar los informes." />;

  const groupReports = reports.data.items.filter(
    (report) => groupForReport(report.filename) === group,
  );
  if (groupReports.length === 0)
    return (
      <EmptyState
        title={definition.emptyMessage}
        detail="Cuando se genere, aparecerá en esta sección."
      />
    );

  return (
    <>
      <p className="mb-4 text-sm leading-6 text-[var(--muted)]">
        La fecha disponible corresponde a la última modificación del archivo.
        La fecha de generación no está disponible; la fecha incluida en el nombre
        se muestra por separado.
      </p>
      <div
        className="table-scroll"
        role="region"
        aria-label="Tabla de informes, desplazamiento horizontal"
        tabIndex={0}
      >
        <table className="data-table">
          <caption className="sr-only">
            Documentos de {definition.title}
          </caption>
          <thead>
            <tr>
              <th scope="col">Informe</th>
              <th scope="col">Fechas del documento</th>
              <th scope="col">Tamaño</th>
              <th scope="col">Acción</th>
            </tr>
          </thead>
          <tbody>
            {groupReports.map((report) => (
              <tr key={report.filename}>
                <td className="min-w-56">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{documentTitles[group]}</span>
                    <Badge>
                      {report.filename.split(".").pop()?.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-[var(--muted)]">
                    {reportFileDate(report.filename)
                      ? `Fecha del nombre: ${reportFileDate(report.filename)}`
                      : "El nombre no contiene una fecha reconocible."}
                  </p>
                  <details className="mt-2 text-xs text-[var(--muted)]">
                    <summary className="min-h-11 cursor-pointer py-3">
                      Ver nombre de archivo
                    </summary>
                    <p className="max-w-72 break-all pb-2">{report.filename}</p>
                  </details>
                </td>
                <td className="min-w-52 text-[var(--muted)]">
                  <p>
                    Última modificación:{" "}
                    <time dateTime={report.modified_at_utc}>
                      {new Date(report.modified_at_utc).toLocaleString("es-CL")}
                    </time>
                  </p>
                  <p className="mt-2 text-xs">
                    Fecha de generación no disponible.
                  </p>
                </td>
                <td className="whitespace-nowrap text-[var(--muted)]">
                  {formatFileSize(report.size_bytes)}
                </td>
                <td>
                  <DocumentLink
                    className="whitespace-nowrap"
                    href={`/api/v1/reports/${encodeURIComponent(report.filename)}`}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Abrir ${documentTitles[group].toLowerCase()} en ${report.filename.split(".").pop()?.toUpperCase()} (${reportFileDate(report.filename) || "fecha no disponible"}), en otra pestaña`}
                  >
                    Abrir informe
                    <span className="sr-only"> en otra pestaña</span>
                  </DocumentLink>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
