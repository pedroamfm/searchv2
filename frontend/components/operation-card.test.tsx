import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OperationCard } from "./operation-card";
import { useJobOperation } from "../lib/use-job-operation";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const job = (status: string, id = "job-1") => ({
  job_id: id,
  job_type: "report",
  status,
  error_code: null,
});

function Fixture() {
  const captureLockRef = useRef<string | null>(null);
  const weekly = useJobOperation({
    id: "weekly",
    jobType: "report",
    scope: "full",
  });
  const rankings = useJobOperation(
    { id: "rankings", jobType: "capture", scope: "daily_highlights" },
    captureLockRef,
  );
  const catalog = useJobOperation(
    { id: "catalog", jobType: "capture", scope: "daily_catalog" },
    captureLockRef,
  );
  return (
    <>
      <OperationCard
        title="Semanal"
        description="Informe"
        action="Generar informe semanal"
        loadingLabel="Generando informe…"
        successLabel="Informe generado."
        reportsHref="/reports/informe-semanal"
        operation={weekly}
        primary
        admin
      />
      <OperationCard
        title="Rankings"
        description="Actualización"
        action="Actualizar rankings"
        loadingLabel="Actualizando rankings…"
        successLabel="Rankings actualizados."
        reportsHref="/reports/ranking-diario"
        operation={rankings}
        admin
        disabledReason={catalog.isLocked ? "Catálogo pendiente." : undefined}
      />
      <OperationCard
        title="Catálogo"
        description="Actualización"
        action="Actualizar catálogo"
        loadingLabel="Actualizando catálogo…"
        successLabel="Catálogo actualizado."
        reportsHref="/reports/catalogo-diario"
        operation={catalog}
        admin
        disabledReason={rankings.isLocked ? "Rankings pendientes." : undefined}
      />
    </>
  );
}
function setup() {
  const submission = deferred<Response>();
  const status = deferred<Response>();
  const fetchMock = vi.fn((url: string, init?: RequestInit) =>
    init?.method === "POST"
      ? submission.promise
      : url.startsWith("/api/v1/jobs/")
        ? status.promise
        : Promise.resolve(json({ items: [] })),
  );
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const view = render(
    <QueryClientProvider client={client}>
      <Fixture />
    </QueryClientProvider>,
  );
  const posts = () =>
    fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
  return { submission, status, fetchMock, invalidate, posts, client, view };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("operation feedback", () => {
  it("responds immediately, blocks rapid duplicates and distinguishes acceptance from completion", async () => {
    const { submission, status, posts, invalidate } = setup();
    const button = screen.getByRole<HTMLButtonElement>("button", {
      name: "Generar informe semanal",
    });
    act(() => {
      button.click();
      button.click();
      button.click();
    });
    expect(button.disabled).toBe(true);
    expect(
      screen.getByRole("button", { name: "Generando informe…" }),
    ).toBeTruthy();
    await waitFor(() => expect(posts()).toHaveLength(1));
    submission.resolve(json(job("queued"), 202));
    await screen.findByText("Solicitud enviada. El trabajo está en cola.");
    expect(screen.queryByText("Informe generado.")).toBeNull();
    expect(button.disabled).toBe(true);
    status.resolve(json(job("succeeded")));
    await screen.findByText("Informe generado.");
    expect(button.disabled).toBe(false);
    expect(
      screen
        .getAllByRole("link", { name: /Ver informes semanales/ })
        .every(
          (link) => link.getAttribute("href") === "/reports/informe-semanal",
        ),
    ).toBe(true);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["reports"] });
    expect(posts()).toHaveLength(1);
  });

  it("keeps daily states independent and prevents simultaneous captures before the next render", async () => {
    const { submission, status, posts } = setup();
    const rankings = screen.getByRole<HTMLButtonElement>("button", {
      name: "Actualizar rankings",
    });
    const catalog = screen.getByRole<HTMLButtonElement>("button", {
      name: "Actualizar catálogo",
    });
    act(() => {
      rankings.click();
      catalog.click();
    });
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(JSON.parse(posts()[0][1]!.body as string).scope).toBe(
      "daily_highlights",
    );
    expect(catalog.disabled).toBe(true);
    expect(
      screen.getByRole<HTMLButtonElement>("button", {
        name: "Generar informe semanal",
      }).disabled,
    ).toBe(false);
    submission.resolve(json(job("queued"), 202));
    status.resolve(json(job("succeeded")));
    await screen.findByText("Rankings actualizados.");
    expect(catalog.disabled).toBe(false);
    expect(screen.queryByText("Catálogo actualizado.")).toBeNull();
  });

  it("announces a confirmed rejection without exposing server details and permits an explicit retry", async () => {
    const { submission, posts } = setup();
    fireEvent.click(
      screen.getByRole("button", { name: "Generar informe semanal" }),
    );
    submission.resolve(
      json(
        { error: { code: "forbidden", message: "internal/path/trace" } },
        403,
      ),
    );
    await screen.findByRole("alert");
    expect(document.body.textContent).not.toContain("internal/path/trace");
    expect(
      screen.getByRole<HTMLButtonElement>("button", {
        name: "Generar informe semanal",
      }).disabled,
    ).toBe(false);
    expect(posts()).toHaveLength(1);
  });

  it.each(["network", "timeout", "server", "invalid-response"])(
    "locks an uncertain %s result without resending automatically",
    async (kind) => {
      const { submission, posts } = setup();
      fireEvent.click(
        screen.getByRole("button", { name: "Generar informe semanal" }),
      );
      if (kind === "network")
        submission.reject(new TypeError("Failed to fetch"));
      else if (kind === "timeout")
        submission.resolve(json({ error: { code: "upstream_timeout" } }, 408));
      else if (kind === "server")
        submission.resolve(json({ error: { code: "internal_error" } }, 503));
      else submission.resolve(json({ accepted: true }, 202));
      await screen.findByText(/No se pudo confirmar el resultado/);
      const button = screen.getByRole<HTMLButtonElement>("button", {
        name: "Generar informe semanal",
      });
      expect(button.disabled).toBe(true);
      fireEvent.click(button);
      expect(posts()).toHaveLength(1);
      expect(
        screen
          .getByRole("link", { name: "Ver historial de trabajos" })
          .getAttribute("href"),
      ).toBe("/captures");
    },
  );

  it("recovers a failed status lookup by querying the same job without a second submission", async () => {
    const { submission, status, fetchMock, posts } = setup();
    fireEvent.click(
      screen.getByRole("button", { name: "Generar informe semanal" }),
    );
    submission.resolve(json(job("queued"), 202));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) => url === "/api/v1/jobs/job-1"),
      ).toBe(true),
    );
    status.reject(new TypeError("Disconnected"));
    await screen.findByText(/No se pudo confirmar el resultado/);
    fetchMock.mockImplementation(() => Promise.resolve(json(job("succeeded"))));
    fireEvent.click(screen.getByRole("button", { name: "Consultar estado" }));
    await screen.findByText("Informe generado.");
    expect(posts()).toHaveLength(1);
  });

  it("shows a terminal job failure without claiming success", async () => {
    const { submission, status } = setup();
    fireEvent.click(
      screen.getByRole("button", { name: "Generar informe semanal" }),
    );
    submission.resolve(json(job("queued"), 202));
    status.resolve(json(job("failed")));
    await screen.findByRole("alert");
    expect(screen.queryByText("Informe generado.")).toBeNull();
  });

  it("aborts the pending status request when the view unmounts", async () => {
    const { submission, fetchMock, view } = setup();
    fireEvent.click(
      screen.getByRole("button", { name: "Generar informe semanal" }),
    );
    submission.resolve(json(job("queued"), 202));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) => url === "/api/v1/jobs/job-1"),
      ).toBe(true),
    );
    const signal = fetchMock.mock.calls.find(
      ([url]) => url === "/api/v1/jobs/job-1",
    )?.[1]?.signal;
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });
});
