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
    expect(screen.getByTestId("svelte-flow__wrapper")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^task-node-/)).toHaveLength(3);
    expect(screen.getByTestId("task-node-FETCH_RAW_DATA")).toBeInTheDocument();
    expect(screen.getByTestId("task-node-TRANSFORM_DATA")).toBeInTheDocument();
    expect(screen.getByTestId("task-node-LOAD_RESULTS")).toBeInTheDocument();
    expect(screen.getByText("Fetches source data")).toBeInTheDocument();
    expect(screen.getAllByText("None")).toHaveLength(2);
    expect(screen.getByText("Transform data")).toBeInTheDocument();
    expect(screen.getAllByText("TRANSFORM_DATA")).toHaveLength(2);
    expect(screen.getByText("Current Launch")).toBeInTheDocument();
    expect(screen.getByText("Latest Launch")).toBeInTheDocument();
    expect(screen.getAllByText("IN_PROGRESS")).toHaveLength(2);
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

  it("shows missing dependency endpoints without creating phantom Task nodes", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        tasks: [
          taskResponse({
            spec_id: "TRANSFORM_DATA",
            label: "Transform data",
            description: "Normalizes source data",
            depends_on: ["FETCH_RAW_DATA"],
            status: "NEW",
          }),
          taskResponse({
            spec_id: "LOAD_RESULTS",
            label: "Load results",
            description: "Persists transformed data",
            depends_on: ["TRANSFORM_DATA", "UNKNOWN_EXPORT"],
            status: "NEW",
          }),
        ],
      }),
    );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));

    expect(await screen.findByText("Transform data")).toBeInTheDocument();
    expect(screen.getByText("Load results")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Missing dependency endpoints: TRANSFORM_DATA depends on FETCH_RAW_DATA; LOAD_RESULTS depends on UNKNOWN_EXPORT",
    );
    expect(screen.getAllByTestId(/^task-node-/)).toHaveLength(2);
    expect(screen.queryByTestId("task-node-FETCH_RAW_DATA")).not.toBeInTheDocument();
    expect(screen.queryByTestId("task-node-UNKNOWN_EXPORT")).not.toBeInTheDocument();
  });

  it("Schedules an eligible Task, shows affected Tasks, and refreshes the selected Scope", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              status: "NEW",
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            tasks: [
              taskResponse({
                spec_id: "FETCH_RAW_DATA",
                label: "Fetch raw data",
                description: "Fetches source data",
                status: "PENDING",
                current_launch: launchResponse(),
              }),
              taskResponse({
                spec_id: "TRANSFORM_DATA",
                label: "Transform data",
                description: "Normalizes source data",
                depends_on: ["FETCH_RAW_DATA"],
                status: "PENDING",
                current_launch: launchResponse("00000000-0000-4000-8000-000000000004"),
              }),
            ],
          },
          202,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              status: "PENDING",
              current_launch: launchResponse(),
            }),
            taskResponse({
              spec_id: "TRANSFORM_DATA",
              label: "Transform data",
              description: "Normalizes source data",
              depends_on: ["FETCH_RAW_DATA"],
              status: "PENDING",
              current_launch: launchResponse("00000000-0000-4000-8000-000000000004"),
            }),
          ],
        }),
      );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Schedule" }));

    expect(
      await screen.findByText("2 Tasks were Scheduled from Fetch raw data."),
    ).toBeInTheDocument();
    expect(screen.getByText("Affected Tasks")).toBeInTheDocument();
    expect(screen.getByText("Fetch raw data, Transform data")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Schedule accepted. Dispatch will continue through reconciliation if queueing is delayed after commit.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("PENDING")).toHaveLength(4);
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/schedule`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(3, `/api/scopes/${scopeId}/tasks`, expect.any(Object));
  });

  it("stops the selected Scope run and refreshes the Task list", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "PENDING",
              current_launch: launchResponse(),
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "FAILED",
              latest_launch: {
                ...launchResponse(),
                status: "FAILED",
                failed_at: "2026-06-05T10:03:00Z",
                is_aborted: true,
              },
            }),
          ],
        }),
      );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Stop Run" }));

    expect(await screen.findByText(`Run for Scope ${scopeId} was stopped.`)).toBeInTheDocument();
    expect(screen.getAllByText("FAILED")).toHaveLength(2);
    expect(screen.getByText("Aborted")).toBeInTheDocument();
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `/api/scopes/${scopeId}/run`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("aborts an active Launch and refreshes the Task view", async () => {
    const launchId = "00000000-0000-4000-8000-000000000003";
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "PENDING",
              current_launch: launchResponse(launchId),
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "FAILED",
              latest_launch: {
                ...launchResponse(launchId),
                status: "FAILED",
                failed_at: "2026-06-05T10:03:00Z",
                is_aborted: true,
              },
            }),
          ],
        }),
      );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Abort Launch" }));

    expect(
      await screen.findByText(`Launch ${launchId} for Fetch raw data was aborted.`),
    ).toBeInTheDocument();
    expect(screen.getAllByText("FAILED")).toHaveLength(2);
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/launches/${launchId}`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("loads and displays a Launch Journal", async () => {
    const launchId = "00000000-0000-4000-8000-000000000003";
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "SUCCESS",
              latest_launch: { ...launchResponse(launchId), status: "FINISHED" },
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          journal: [
            {
              id: "00000000-0000-4000-8000-000000000004",
              message: "Handler started",
              level: "INFO",
              type: "UNCLASSIFIED",
              timestamp: "2026-06-05T16:53:52.956653+00:00",
            },
          ],
        }),
      );

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Open Journal" }));

    expect(await screen.findByText("Launch Journal")).toBeInTheDocument();
    expect(screen.getByText("Handler started")).toBeInTheDocument();
    expect(screen.getByText("INFO")).toBeInTheDocument();
    expect(screen.getByText("UNCLASSIFIED")).toBeInTheDocument();
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/launches/${launchId}/journal`,
      expect.any(Object),
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

  it("clears the stored API key after a 401 Schedule response", async () => {
    localStorage.setItem("task-orchestrator.api-key", "expired-key");
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              status: "NEW",
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "Invalid API key" }, 401));

    render(App);

    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Schedule" }));

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

  it("shows a Schedule-specific message for a missing Scope or unknown Task", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              status: "NEW",
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "Task was not found" }, 404));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Schedule" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That Task or Scope was not found. Refresh the selected Scope and try again.",
    );
  });

  it("shows a stop-run message for a missing Scope", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ tasks: [] }))
      .mockResolvedValueOnce(jsonResponse({ detail: "Job was not found" }, 404));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Stop Run" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No Scope exists for that run. Initialize it first or enter another Scope ID.",
    );
  });

  it("shows an abort message for an unknown Task or missing Launch", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "PENDING",
              current_launch: launchResponse(),
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "Launch was not found" }, 404));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Abort Launch" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That Scope, Task, or Launch was not found. Refresh the selected Scope and try again.",
    );
  });

  it("shows a Schedule-specific message when the Task cannot be Scheduled", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              status: "NEW",
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "Invalid task status" }, 422));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Schedule" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That Task cannot be Scheduled in its current state.",
    );
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

  it("shows generated-contract validation failures for invalid Schedule responses", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              status: "NEW",
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ tasks: [{ id: "not-a-uuid" }] }, 202));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Schedule" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The Schedule response from the server did not match the generated API contract.",
    );
  });

  it("shows generated-contract validation failures for invalid Journal responses", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              status: "SUCCESS",
              latest_launch: { ...launchResponse(), status: "FINISHED" },
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ journal: [{ id: "not-a-uuid" }] }));

    render(App);

    await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
    await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
    await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
    await fireEvent.click(await screen.findByRole("button", { name: "Open Journal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The Journal response from the server did not match the generated API contract.",
    );
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

function taskResponse(overrides: Record<string, unknown>) {
  return {
    id: "00000000-0000-4000-8000-000000000002",
    spec_id: "FETCH_RAW_DATA",
    label: "Fetch raw data",
    description: "Fetches source data",
    depends_on: [],
    status: "NEW",
    current_launch: null,
    latest_launch: null,
    ...overrides,
  };
}

function launchResponse(id = "00000000-0000-4000-8000-000000000003") {
  return {
    id,
    scheduled_at: "2026-06-05T10:00:00Z",
    scheduled_by: "secret-key",
    status: "PENDING",
    started_at: null,
    finished_at: null,
    failed_at: null,
    skipped_at: null,
    is_aborted: null,
  };
}
