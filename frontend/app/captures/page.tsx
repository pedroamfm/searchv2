"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent } from "react";
import { useCurrentUser } from "@/components/auth-gate";
import { WorkspacePage } from "@/components/page-template";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { ApiClientError, getApi, postApi } from "@/lib/api-client";
type Job = {
  job_id: string;
  job_type: string;
  status: string;
  step_code: string | null;
  created_at_utc: string;
  error_message: string | null;
};
const csrf = () =>
  document.cookie
    .split("; ")
    .find((entry) => entry.startsWith("product_radar_csrf="))
    ?.split("=")[1];
export default function CapturesPage() {
  const user = useCurrentUser();
  const client = useQueryClient();
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => getApi<{ items: Job[] }>("/jobs"),
    refetchInterval: 3000,
  });
  const create = useMutation({
    mutationFn: () =>
      postApi<Job>(
        "/jobs",
        {
          job_type: "capture",
          source_code: "mercado_libre",
          site_id: "MLC",
          scope: "full",
        },
        csrf(),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: ["jobs"] }),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate();
  };
  return (
    <WorkspacePage
      eyebrow="Operación"
      title="Capturas"
      description="Una solicitud sólo encola la captura. El worker la ejecuta fuera del proceso HTTP y conserva su historial."
    >
      {user.data?.role === "admin" ? (
        <Card>
          <h2 className="font-semibold">Nueva captura completa</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Mercado Libre Chile (MLC). La adquisición puede tardar varios
            minutos y usa las credenciales configuradas sólo en el worker.
          </p>
          <form className="mt-4" onSubmit={submit}>
            <Button
              variant="primary"
              loading={create.isPending}
              loadingLabel="Encolando…"
              type="submit"
            >
              Confirmar y encolar
            </Button>
          </form>
          {create.isError ? (
            <div className="mt-3">
              <ErrorState
                message={
                  create.error instanceof ApiClientError
                    ? create.error.message
                    : "No se pudo encolar la captura."
                }
              />
            </div>
          ) : null}
        </Card>
      ) : (
        <Card>
          <p className="text-sm text-[var(--muted)]">
            Sólo administradores pueden iniciar capturas.
          </p>
        </Card>
      )}
      <section className="mt-5">
        <h2 className="mb-3 font-semibold">Historial de trabajos</h2>
        {jobs.isPending ? (
          <Skeleton className="h-40" />
        ) : jobs.isError ? (
          <ErrorState message="No fue posible cargar los trabajos." />
        ) : jobs.data.items.length ? (
          <div className="overflow-x-auto rounded-xl border border-[var(--line)]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--surface-soft)] text-[var(--muted)]">
                <tr>
                  <th className="p-3">Tipo</th>
                  <th className="p-3">Estado</th>
                  <th className="p-3">Etapa</th>
                  <th className="p-3">Creado</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.items.map((job) => (
                  <tr
                    className="border-t border-[var(--line)]"
                    key={job.job_id}
                  >
                    <td className="p-3">{job.job_type}</td>
                    <td className="p-3">{job.status}</td>
                    <td className="p-3">{job.step_code || "—"}</td>
                    <td className="p-3">
                      {new Date(job.created_at_utc).toLocaleString("es-CL")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Aún no hay trabajos"
            detail="Las capturas encoladas aparecerán aquí."
          />
        )}
      </section>
    </WorkspacePage>
  );
}
