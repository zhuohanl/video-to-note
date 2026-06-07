import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "../app/login/page";
import { middleware } from "../middleware";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

describe("login", () => {
  beforeEach(() => {
    push.mockReset();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("posts credentials and routes to submit on success", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("{}", { status: 200 }));
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "local" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/submit"));
    expect(fetch).toHaveBeenCalledWith("/login", {
      body: JSON.stringify({ username: "local", password: "secret" }),
      credentials: "include",
      headers: { "content-type": "application/json" },
      method: "POST",
    });
  });

  it("shows the API envelope message on 401", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: "unauthorized", message: "Bad login" } }), {
        status: 401,
      }),
    );
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "local" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Bad login");
    expect(push).not.toHaveBeenCalled();
  });

  it("redirects unauthenticated guarded route access to login", () => {
    const request = new NextRequest("https://vtn.test/review/job-1");

    const response = middleware(request);

    expect(response?.status).toBe(307);
    expect(response?.headers.get("location")).toBe("https://vtn.test/login");
  });

  it("allows guarded routes when the session cookie is present", () => {
    const request = new NextRequest("https://vtn.test/submit", {
      headers: { cookie: "vtn_session=signed" },
    });

    expect(middleware(request)).toBeUndefined();
  });
});
