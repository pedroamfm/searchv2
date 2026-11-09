import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

type InteractionStyle = {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
};

function interactionClass(
  { variant = "secondary", size = "md" }: InteractionStyle,
  className = "",
) {
  return `control control--${variant} control--${size} ${className}`;
}

export function Button({
  variant,
  size,
  loading = false,
  loadingLabel = "Cargando…",
  children,
  className,
  disabled,
  type = "button",
  ...props
}: ComponentProps<"button"> &
  InteractionStyle & { loading?: boolean; loadingLabel?: string }) {
  return (
    <button
      {...props}
      type={type}
      className={interactionClass({ variant, size }, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      <span
        className={`control__content ${loading ? "invisible" : ""}`}
        aria-hidden={loading || undefined}
      >
        {children}
      </span>
      {loading ? (
        <span className="control__loading">
          <span className="activity" aria-hidden="true" />
          {loadingLabel}
        </span>
      ) : null}
    </button>
  );
}

export function ButtonLink({
  variant,
  size,
  className,
  ...props
}: ComponentProps<typeof Link> & InteractionStyle) {
  return (
    <Link
      {...props}
      className={interactionClass({ variant, size }, className)}
    />
  );
}

export function DocumentLink({
  className = "",
  ...props
}: ComponentProps<"a">) {
  return (
    <a
      {...props}
      className={interactionClass({ variant: "ghost", size: "sm" }, className)}
    />
  );
}

export function Badge({
  children,
  tone = "neutral",
}: Readonly<{
  children: ReactNode;
  tone?: "neutral" | "success" | "warning";
}>) {
  const tones = {
    neutral:
      "border-[var(--line)] bg-[var(--surface-soft)] text-[var(--muted)]",
    success: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    warning: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  };
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Card({
  children,
  className = "",
}: Readonly<{ children: ReactNode; className?: string }>) {
  return (
    <section
      className={`rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-sm ${className}`}
    >
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  detail,
}: Readonly<{ title: string; detail: string }>) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--line)] p-8 text-center">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{detail}</p>
    </div>
  );
}

export function ErrorState({
  message,
  requestId,
}: Readonly<{ message: string; requestId?: string | null }>) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-100"
    >
      <p className="font-medium">No pudimos cargar esta información.</p>
      <p className="mt-1 text-rose-100/80">{message}</p>
      {requestId ? (
        <p className="mt-2 text-xs text-rose-100/65">
          ID de solicitud: {requestId}
        </p>
      ) : null}
    </div>
  );
}

export function Skeleton({ className = "" }: Readonly<{ className?: string }>) {
  return (
    <div
      aria-label="Cargando"
      className={`animate-pulse rounded-lg bg-[var(--surface-soft)] ${className}`}
    />
  );
}

export function ChartFrame({
  title,
  unit,
  children,
  table,
}: Readonly<{
  title: string;
  unit: string;
  children: ReactNode;
  table: ReactNode;
}>) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Unidad: {unit}</p>
        </div>
        <Badge>Próximamente</Badge>
      </div>
      <div className="mt-5">{children}</div>
      <details className="mt-5">
        <summary className="cursor-pointer text-sm text-[var(--accent)]">
          Ver alternativa tabular
        </summary>
        <div className="mt-3 overflow-x-auto">{table}</div>
      </details>
    </Card>
  );
}
