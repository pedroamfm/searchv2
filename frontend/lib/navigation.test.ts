import { describe, expect, it } from "vitest";

import { NAVIGATION_ITEMS } from "./navigation";

describe("navigation", () => {
  it("keeps the six MVP workspaces unique", () => {
    const titles = NAVIGATION_ITEMS.map((item) => item.title);

    expect(titles).toHaveLength(6);
    expect(new Set(titles).size).toBe(titles.length);
    expect(NAVIGATION_ITEMS.map((item) => item.href)).toEqual([
      "/",
      "/trends",
      "/products",
      "/captures",
      "/reports",
      "/system",
    ]);
  });
});
