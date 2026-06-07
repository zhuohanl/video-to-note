import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "../app/page";

describe("web smoke", () => {
  it("renders the app shell", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "Video-to-Note" })).toBeInTheDocument();
  });
});
