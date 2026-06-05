import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.svelte";

const scopeId = "00000000-0000-4000-8000-000000000001";

describe("operator tracer", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("stores the API key, initializes a Scope, and shows tasks", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ scope_id: scopeId }, 201))
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            {
              id: "00000000-0000-4000-8000-000000000002",
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              depends_on: [],
              status: "NEW",
              current_launch: null,
              latest_launch: null,
            },
          ],
        }),
      );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Initialize Scope" }));

    expect(await screen.findByText("Fetch raw data")).toBeInTheDocument();
    expect(localStorage.getItem("task-orchestrator.api-key")).toBe("secret-key");
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-Key": "secret-key" }),
      }),
    );
  });

  it("clears the stored API key after a 401 response", async () => {
    localStorage.setItem("task-orchestrator.api-key", "expired-key");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Invalid API key" }, 401));

    render(App);

    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The API key was rejected");
    expect(localStorage.getItem("task-orchestrator.api-key")).toBeNull();
    expect(screen.getByLabelText("API key")).toHaveValue("");
  });

  it("shows a direct message when selecting a missing Scope", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Job was not found" }, 404));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No Scope exists for that ID");
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
