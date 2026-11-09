"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { WorkspacePage } from "@/components/page-template";
import { ButtonLink, Card, ErrorState, Skeleton } from "@/components/ui";
import { ApiClientError, getApi } from "@/lib/api-client";

type Raw = {
  raw_source_id: number;
  source_code: string;
  endpoint: string | null;
  captured_at_utc: string;
  http_status: number | null;
  sha256: string;
  relative_path: string;
};
export default function EvidencePage() {
  const { rawSourceId } = useParams<{ rawSourceId: string }>();
  const evidence = useQuery({
    queryKey: ["raw-source", rawSourceId],
    queryFn: () => getApi<Raw>(`/raw-sources/${rawSourceId}`),
  });
  if (evidence.isPending)
    return (
      <WorkspacePage
        eyebrow="Evidencia"
        title="Cargando metadata RAW"
        description="Verificando la procedencia capturada."
      >
        <Skeleton className="h-48" />
      </WorkspacePage>
    );
  if (evidence.isError)
    return (
      <WorkspacePage
        eyebrow="Evidencia"
        title="Evidencia no disponible"
        description="La metadata solicitada no se encontró."
      >
        <ErrorState
          message={
            evidence.error instanceof ApiClientError
              ? evidence.error.message
              : "No fue posible cargar la evidencia."
          }
        />
      </WorkspacePage>
    );
  const raw = evidence.data;
  return (
    <WorkspacePage
      eyebrow="Evidencia"
      title={`RAW #${raw.raw_source_id}`}
      description="Metadata verificable de la fuente preservada; la descarga directa no se expone en la interfaz."
    >
      <ButtonLink
        variant="ghost"
        size="sm"
        href="/trends"
      >
        ← Volver a tendencias
      </ButtonLink>
      <Card className="mt-4">
        <dl className="grid gap-4 text-sm md:grid-cols-2">
          <div>
            <dt className="text-[var(--muted)]">Fuente</dt>
            <dd>{raw.source_code}</dd>
          </div>
          <div>
            <dt className="text-[var(--muted)]">Capturada</dt>
            <dd>{new Date(raw.captured_at_utc).toLocaleString("es-CL")}</dd>
          </div>
          <div>
            <dt className="text-[var(--muted)]">Endpoint</dt>
            <dd>{raw.endpoint || "No informado"}</dd>
          </div>
          <div>
            <dt className="text-[var(--muted)]">HTTP</dt>
            <dd>{raw.http_status ?? "No informado"}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-[var(--muted)]">SHA-256</dt>
            <dd className="break-all font-mono text-xs">{raw.sha256}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-[var(--muted)]">Ruta relativa preservada</dt>
            <dd className="break-all font-mono text-xs">{raw.relative_path}</dd>
          </div>
        </dl>
      </Card>
    </WorkspacePage>
  );
}
