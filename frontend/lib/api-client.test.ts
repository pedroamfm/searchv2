import { afterEach, describe, expect, it, vi } from "vitest";

import { getApi } from "./api-client";

describe("getApi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns JSON and sends a same-origin request ID", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getApi<{ items: unknown[] }>("/sources")).resolves.toEqual({ items: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/sources",
      expect.objectContaining({ headers: expect.objectContaining({ "X-Request-ID": expect.any(String) }) }),
    );
  });

  it("normalizes the API error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "resource_not_found", message: "No existe", request_id: "req-1" } }), { status: 404 }),
      ),
    );

    await expect(getApi("/missing")).rejects.toMatchObject({
      code: "resource_not_found",
      requestId: "req-1",
      status: 404,
    });
  });
});
