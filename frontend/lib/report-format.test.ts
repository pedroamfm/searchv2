import { describe, expect, it } from "vitest";
import { formatFileSize, reportFileDate } from "./report-format";

describe("document metadata formatting", () => {
  it("uses consistent decimal size units", () => {
    expect(formatFileSize(132000)).toBe("132 KB");
    expect(formatFileSize(2400000)).toBe("2,4 MB");
    expect(formatFileSize(0)).toBe("0 B");
  });
  it("recognizes calendar dates without treating them as generation timestamps", () => {
    expect(
      reportFileDate("product_radar_MLC_20261004_32_categorias_online.md"),
    ).toMatch(/4.*oct.*2026/);
    expect(
      reportFileDate("product_radar_MLC_20260919_123116_daily_catalog.md"),
    ).toMatch(/19.*sept.*2026/);
    expect(
      reportFileDate("product_radar_MLC_20260231_32_categorias_online.md"),
    ).toBeNull();
    expect(reportFileDate("product_radar_MLC_unknown.md")).toBeNull();
  });
});
