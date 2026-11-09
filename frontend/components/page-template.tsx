import type { ReactNode } from "react";

import { ArchitectureStatus } from "@/components/architecture-status";
import { Badge, Card, ChartFrame, EmptyState, Skeleton } from "@/components/ui";

export function WorkspacePage({
  title,
  eyebrow,
  description,
  children,
}: Readonly<{
  title: string;
  eyebrow: string;
  description: string;
  children?: ReactNode;
}>) {
  return (
    <main
      id="main-content"
      className="mx-auto w-full min-w-0 max-w-7xl px-5 py-7 sm:px-8 lg:px-10 lg:py-10"
    >
      <header className="flex flex-col gap-6 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
            {eyebrow}
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
            {title}
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-[var(--muted)]">
            {description}
          </p>
        </div>
        <ArchitectureStatus />
      </header>
      <div className="py-8">{children}</div>
    </main>
  );
}

export function PlaceholderWorkspace({
  title,
  description,
}: Readonly<{ title: string; description: string }>) {
  return (
    <WorkspacePage
      title={title}
      eyebrow="MVP web v0.1"
      description={description}
    >
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <Skeleton className="h-4 w-24" />
          <Skeleton className="mt-4 h-8 w-16" />
          <p className="mt-4 text-sm text-[var(--muted)]">
            Estado de carga reutilizable
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--muted)]">Fuente</p>
          <p className="mt-3 text-2xl font-semibold">Mercado Libre</p>
          <div className="mt-4">
            <Badge tone="success">MLC</Badge>
          </div>
        </Card>
        <Card>
          <p className="text-sm text-[var(--muted)]">Siguiente entrega</p>
          <p className="mt-3 font-medium">Datos reales y filtros</p>
        </Card>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <ChartFrame
          title="Evolución"
          unit="posición en ranking"
          table={
            <table className="w-full text-left text-sm">
              <caption className="sr-only">
                Datos alternativos del gráfico
              </caption>
              <tbody>
                <tr>
                  <td className="py-2">Sin series aún</td>
                  <td className="text-right text-[var(--muted)]">B05</td>
                </tr>
              </tbody>
            </table>
          }
        >
          <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-[var(--line)] text-sm text-[var(--muted)]">
            Área reservada para gráfico accesible
          </div>
        </ChartFrame>
        <Card>
          <EmptyState
            title="Aún no hay datos en esta vista"
            detail="La estructura visual, estados y navegación ya están preparados para la siguiente entrega funcional."
          />
        </Card>
      </div>
    </WorkspacePage>
  );
}
