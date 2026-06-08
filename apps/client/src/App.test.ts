import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.svelte";
import { jsonResponse, launchResponse, scopeId, taskResponse } from "./test/fixtures";

describe("Task DAG console", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("loads a Scope, renders Task nodes, and opens the inspector", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        tasks: [
          taskResponse({ spec_id: "FETCH_RAW_DATA", label: "Fetch raw data" }),
          taskResponse({
            spec_id: "TRANSFORM_DATA",
            label: "Transform data",
            description: "Normalizes source data",
            depends_on: ["FETCH_RAW_DATA"],
            status: "IN_PROGRESS",
          }),
          taskResponse({
            spec_id: "LOAD_RESULTS",
            label: "Load results",
            depends_on: ["TRANSFORM_DATA"],
          }),
        ],
      }),
    );

    render(App);
    await selectScope();
    await fireEvent.click(await screen.findByTestId("task-node-TRANSFORM_DATA"));

    const inspector = await screen.findByRole("complementary", { name: "Task inspector" });
    expect(within(inspector).getByRole("heading", { name: "Transform data" })).toBeInTheDocument();
    expect(within(inspector).getByText("IN_PROGRESS")).toBeInTheDocument();
    expect(screen.getByTestId("task-node-FETCH_RAW_DATA")).toHaveClass("task-flow-node-upstream");
    expect(screen.getByTestId("task-node-LOAD_RESULTS")).toHaveClass("task-flow-node-downstream");
    expect(screen.queryByText("Selected")).not.toBeInTheDocument();
    expect(screen.queryByText("Upstream")).not.toBeInTheDocument();
    expect(screen.queryByText("Downstream")).not.toBeInTheDocument();
  });

  it("reports missing dependency endpoints without creating phantom Task nodes", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        tasks: [
          taskResponse({
            spec_id: "TRANSFORM_DATA",
            label: "Transform data",
            depends_on: ["FETCH_RAW_DATA"],
          }),
          taskResponse({
            spec_id: "LOAD_RESULTS",
            label: "Load results",
            depends_on: ["TRANSFORM_DATA", "UNKNOWN_EXPORT"],
          }),
        ],
      }),
    );

    render(App);
    await selectScope();

    expect(await screen.findByText("Transform data")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Missing dependency endpoints: TRANSFORM_DATA depends on FETCH_RAW_DATA; LOAD_RESULTS depends on UNKNOWN_EXPORT",
    );
    expect(screen.getAllByTestId(/^task-node-/)).toHaveLength(2);
    expect(screen.queryByTestId("task-node-FETCH_RAW_DATA")).not.toBeInTheDocument();
  });

  it("keeps active-work polling quiet and stops after terminal state", async () => {
    vi.useFakeTimers();
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              status: "PENDING",
              current_launch: launchResponse(),
            }),
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [
            taskResponse({
              status: "SUCCESS",
              latest_launch: {
                ...launchResponse(),
                status: "FINISHED",
                finished_at: "2026-06-05T10:08:00Z",
              },
            }),
          ],
        }),
      );

    render(App);
    await selectScope();
    expect(await screen.findByText("PENDING")).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(5_000);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("SUCCESS")).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(5_000);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("wires inspector Task actions through the selected Scope", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [taskResponse({ status: "NEW" })],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            tasks: [taskResponse({ status: "PENDING", current_launch: launchResponse() })],
          },
          202,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          tasks: [taskResponse({ status: "PENDING", current_launch: launchResponse() })],
        }),
      );

    render(App);
    await selectScope();
    await fireEvent.click(await screen.findByTestId("task-node-FETCH_RAW_DATA"));
    const inspector = await screen.findByRole("complementary", { name: "Task inspector" });
    await fireEvent.click(within(inspector).getByRole("button", { name: "Schedule" }));

    expect(
      await screen.findByText("1 Task was Scheduled from Fetch raw data."),
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/schedule`,
      expect.objectContaining({ method: "POST" }),
    );
  });
});

async function selectScope() {
  await fireEvent.input(screen.getByLabelText("API key"), { target: { value: "secret-key" } });
  await fireEvent.input(screen.getByLabelText("Scope ID"), { target: { value: scopeId } });
  await fireEvent.click(screen.getByRole("button", { name: "Select Scope" }));
}
