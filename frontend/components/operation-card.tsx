"use client";

import { Button, ButtonLink, Card } from "@/components/ui";
import type { useJobOperation } from "@/lib/use-job-operation";

type Props = {
  title: string;
  description: string;
  action: string;
  loadingLabel: string;
  successLabel: string;
  reportsHref: string;
  operation: ReturnType<typeof useJobOperation>;
  primary?: boolean;
  admin: boolean;
  disabledReason?: string;
};

export function OperationCard({
  title,
  description,
  action,
  loadingLabel,
  successLabel,
  reportsHref,
  operation,
  primary,
  admin,
  disabledReason,
}: Props) {
  const message =
    operation.uncertain || operation.checkingFailed
      ? "No se pudo confirmar el resultado. Consulta el historial de trabajos antes de enviar otra solicitud."
      : operation.conflict
        ? "Ya hay una captura en curso. Espera a que termine para actualizar los datos."
        : operation.state === "error"
          ? "No se pudo completar la operación. Revisa el historial de trabajos antes de volver a intentarlo."
          : operation.state === "success"
            ? successLabel
            : operation.submitting
              ? loadingLabel
              : operation.job?.status === "queued"
                ? "Solicitud enviada. El trabajo está en cola."
                : operation.state === "running"
                  ? loadingLabel
                  : "";
  const reasonId = `reason-${reportsHref.split("/").pop()}`;
  const statusId = `${reasonId}-status`;
  return (
    <Card
      className={`flex min-w-0 flex-col lg:row-span-3 lg:grid lg:grid-rows-subgrid ${primary ? "border-[var(--control-border)]" : ""}`}
    >
      <div>
        <h2 className="font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
          {description}
        </p>
      </div>
      <div className="mt-auto pt-5">
        {admin ? (
          <Button
            className="w-full"
            variant={primary ? "primary" : "secondary"}
            loading={operation.state === "running"}
            loadingLabel={loadingLabel}
            disabled={operation.isLocked || !!disabledReason}
            aria-describedby={
              operation.isLocked
                ? statusId
                : disabledReason
                  ? reasonId
                  : undefined
            }
            onClick={operation.start}
          >
            {action}
          </Button>
        ) : (
          <p className="min-h-11 text-sm text-[var(--muted)]">
            Sólo administradores pueden iniciar esta operación.
          </p>
        )}
        <div className="mt-2 min-h-11">
          {primary ? (
            <ButtonLink
              className="w-full"
              variant="ghost"
              size="sm"
              href={reportsHref}
            >
              Ver informes semanales
            </ButtonLink>
          ) : operation.state === "success" ? (
            <ButtonLink
              className="w-full"
              variant="ghost"
              size="sm"
              href={reportsHref}
            >
              Ver informes de esta actualización
            </ButtonLink>
          ) : null}
        </div>
      </div>
      <div>
        <div
          id={statusId}
          role={operation.state === "error" ? "alert" : "status"}
          aria-atomic="true"
          className={`mt-3 min-h-12 text-sm leading-6 ${operation.state === "error" ? "text-rose-200" : operation.state === "success" ? "text-[var(--accent)]" : "text-[var(--muted)]"}`}
        >
          {message ? <p>{message}</p> : null}
        </div>
        {disabledReason && !operation.isLocked ? (
          <p id={reasonId} className="mt-2 text-sm text-[var(--muted)]">
            {disabledReason}
          </p>
        ) : null}
        {operation.checkingFailed ? (
          <Button
            className="mt-2"
            variant="secondary"
            size="sm"
            onClick={operation.checkStatus}
          >
            Consultar estado
          </Button>
        ) : null}
        {operation.state === "error" ? (
          <ButtonLink variant="ghost" size="sm" href="/captures">
            Ver historial de trabajos
          </ButtonLink>
        ) : null}
      </div>
    </Card>
  );
}
