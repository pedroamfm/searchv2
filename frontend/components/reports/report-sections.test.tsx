import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReportGroupDocuments } from "./report-sections";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
describe("report documents", () => {
  it("keeps formats separate, uses modification metadata and preserves original file routes", async () => {
    const files = ["md", "pdf"].map((ext) => ({
      filename: `product_radar_MLC_20261004_32_categorias_online.${ext}`,
      modified_at_utc: "2026-10-05T15:00:00Z",
      size_bytes: ext === "md" ? 132000 : 2400000,
    }));
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ items: files }), {
            headers: { "Content-Type": "application/json" },
          }),
        ),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReportGroupDocuments group="weekly" />
      </QueryClientProvider>,
    );
    const links = await screen.findAllByRole("link", {
      name: /Abrir informe semanal/,
    });
    expect(links).toHaveLength(2);
    expect(links.map((link) => link.getAttribute("href"))).toEqual(
      files.map(
        (file) => `/api/v1/reports/${encodeURIComponent(file.filename)}`,
      ),
    );
    expect(
      screen.getAllByText("Fecha de generación no disponible."),
    ).toHaveLength(2);
    expect(
      document.querySelectorAll('time[datetime="2026-10-05T15:00:00Z"]'),
    ).toHaveLength(2);
    expect(screen.getByText("132 KB")).toBeTruthy();
    expect(screen.getByText("2,4 MB")).toBeTruthy();
    expect(screen.getByText(files[0].filename)).toBeTruthy();
    expect(screen.getAllByText(/Fecha del nombre: 4.*oct.*2026/)).toHaveLength(
      2,
    );
  });
});
