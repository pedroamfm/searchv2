import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState, ErrorState } from "./ui";

describe("workspace states", () => {
  it("exposes empty and error states to assistive technology", () => {
    render(<><EmptyState title="Sin datos" detail="Todavía no hay resultados." /><ErrorState message="La API no respondió." requestId="request-7" /></>);

    expect(screen.getByText("Sin datos")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("request-7");
  });
});
