import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import TrendsPage from "./page";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const trend = (keyword: string, position: number) => ({
  source_code: "mercado_libre",
  site_id: "MLC",
  keyword,
  position,
  previous_position: null,
  change: "new",
  scope: "category",
  category_id: "MLC1000",
  captured_at_utc: "2026-10-04T12:00:00Z",
  raw_source_id: 65,
});
function setup(
  history: (url: string, init?: RequestInit) => Promise<Response>,
) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (url.includes("/trends/history")) return history(url, init);
    if (url.includes("/trends?"))
      return Promise.resolve(
        json({
          items: [trend("alarma", 1), trend("audífonos", 2)],
          page: { next_cursor: 50 },
        }),
      );
    if (url.includes("/categories"))
      return Promise.resolve(
        json({
          items: [
            { category_id: "MLC1000", name: "Electrónica, Audio y Video" },
          ],
        }),
      );
    return Promise.resolve(json({ status: "ok" }));
  });
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <TrendsPage />
    </QueryClientProvider>,
  );
  return { fetchMock, view };
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("trend history", () => {
  it("opens a visible modal, contains focus, closes with Escape and restores its trigger and filters", async () => {
    setup(() => Promise.resolve(json({ items: [trend("alarma", 1)] })));
    await screen.findByRole("button", { name: "Ver historial de alarma" });
    fireEvent.change(screen.getByRole("textbox", { name: "Buscar término" }), {
      target: { value: "alar" },
    });
    const trigger = await screen.findByRole("button", {
      name: "Ver historial de alarma",
    });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Historial: alarma" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(document.activeElement).toBe(within(dialog).getByRole("heading"));
    expect(within(dialog).getByText(/Electrónica, Audio y Video/)).toBeTruthy();
    fireEvent.keyDown(document.activeElement!, { key: "Tab", shiftKey: true });
    const close = within(dialog).getByRole("button", {
      name: "Cerrar historial",
    });
    expect(document.activeElement).toBe(close);
    fireEvent.keyDown(close, { key: "Tab" });
    expect(document.activeElement).toBe(close);
    fireEvent.keyDown(close, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(trigger);
    expect(
      screen.getByRole<HTMLInputElement>("textbox", { name: "Buscar término" })
        .value,
    ).toBe("alar");
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("shows an empty history without inventing a zero observation", async () => {
    setup(() => Promise.resolve(json({ items: [] })));
    fireEvent.click(
      await screen.findByRole("button", { name: "Ver historial de alarma" }),
    );
    await screen.findByText("Sin observaciones disponibles");
    expect(
      within(screen.getByRole("dialog")).queryByText(/Posición 0/),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar historial" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("distinguishes a query error from absence of observations and allows retry", async () => {
    let failed = true;
    setup(() =>
      Promise.resolve(
        failed
          ? json({ error: { message: "raw internal trace" } }, 500)
          : json({ items: [trend("alarma", 7)] }),
      ),
    );
    fireEvent.click(
      await screen.findByRole("button", { name: "Ver historial de alarma" }),
    );
    await screen.findByRole("alert");
    expect(screen.queryByText("Sin observaciones disponibles")).toBeNull();
    expect(document.body.textContent).not.toContain("raw internal trace");
    failed = false;
    fireEvent.click(
      screen.getByRole("button", { name: "Reintentar consulta" }),
    );
    await screen.findByText("Posición 7");
  });

  it("cancels stale histories and keys the term independently from the shared RAW source", async () => {
    const responses = new Map<string, (response: Response) => void>();
    const { fetchMock } = setup(
      (url) =>
        new Promise((resolve) =>
          responses.set(
            new URL(`http://local${url}`).searchParams.get("keyword")!,
            resolve,
          ),
        ),
    );
    const alarm = await screen.findByRole("button", {
      name: "Ver historial de alarma",
    });
    const headphones = screen.getByRole("button", {
      name: "Ver historial de audífonos",
    });
    fireEvent.click(alarm);
    await waitFor(() => expect(responses.has("alarma")).toBe(true));
    const first = fetchMock.mock.calls.find(([url]) =>
      url.includes("/trends/history"),
    )?.[1]?.signal;
    // Simulate a second selection arriving before the first request has finished.
    fireEvent.click(headphones);
    await waitFor(() => expect(responses.has("audífonos")).toBe(true));
    expect(first?.aborted).toBe(true);
    await act(async () => {
      responses.get("audífonos")!(json({ items: [trend("audífonos", 9)] }));
    });
    await screen.findByText("Posición 9");
    await act(async () => {
      responses.get("alarma")!(json({ items: [trend("alarma", 99)] }));
    });
    expect(screen.queryByText("Posición 99")).toBeNull();
    expect(
      screen.getByRole("dialog", { name: "Historial: audífonos" }),
    ).toBeTruthy();
  });
});
