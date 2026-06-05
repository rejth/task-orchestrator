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

  it("stores the API key, initializes a Scope, and shows the Task console details", async () => {
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
            {
              id: "00000000-0000-4000-8000-000000000003",
              spec_id: "TRANSFORM_DATA",
              label: "Transform data",
              description: "Normalizes source data",
              depends_on: ["FETCH_RAW_DATA"],
              status: "IN_PROGRESS",
              current_launch: {
                id: "00000000-0000-4000-8000-000000000004",
                scheduled_at: "2026-06-05T10:00:00Z",
                scheduled_by: "secret-key",
                status: "IN_PROGRESS",
                started_at: "2026-06-05T10:01:00Z",
                finished_at: null,
                failed_at: null,
                skipped_at: null,
                is_aborted: false,
              },
              latest_launch: null,
            },
            {
              id: "00000000-0000-4000-8000-000000000005",
              spec_id: "LOAD_RESULTS",
              label: "Load results",
              description: "Persists transformed data",
              depends_on: ["TRANSFORM_DATA"],
              status: "SUCCESS",
              current_launch: null,
              latest_launch: {
                id: "00000000-0000-4000-8000-000000000006",
                scheduled_at: "2026-06-05T10:05:00Z",
                scheduled_by: "secret-key",
                status: "SUCCESS",
                started_at: "2026-06-05T10:06:00Z",
                finished_at: "2026-06-05T10:08:00Z",
                failed_at: null,
                skipped_at: null,
                is_aborted: false,
              },
            },
          ],
        }),
      );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Initialize Scope" }));

    expect(await screen.findByText("Fetch raw data")).toBeInTheDocument();
    expect(screen.getByText("Fetches source data")).toBeInTheDocument();
    expect(screen.getAllByText("None")).toHaveLength(2);
    expect(screen.getByText("Transform data")).toBeInTheDocument();
    expect(screen.getAllByText("TRANSFORM_DATA")).toHaveLength(2);
    expect(screen.getByText("Current Launch")).toBeInTheDocument();
    expect(screen.getByText("Latest Launch")).toBeInTheDocument();
    expect(screen.getAllByText("IN PROGRESS")).toHaveLength(2);
    expect(localStorage.getItem("task-orchestrator.api-key")).toBe("secret-key");
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-Key": "secret-key" }),
      }),
    );
  });

  it("shows an empty Job state for a selected Scope with no Tasks", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ tasks: [] }));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));

    expect(
      await screen.findByText("This Scope does not have any Tasks in its Job."),
    ).toBeInTheDocument();
    expect(screen.getByText(scopeId)).toBeInTheDocument();
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

  it("shows generated-contract validation failures for invalid Task lists", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ tasks: [{ id: "not-a-uuid" }] }));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The Task list from the server did not match the generated API contract.",
    );
    expect(
      screen.getByText("Select or initialize a Scope to load its Job Task list."),
    ).toBeInTheDocument();
  });

  it("shows server error details when Task loading fails", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ detail: "Database is unavailable" }, 500),
    );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Database is unavailable");
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
