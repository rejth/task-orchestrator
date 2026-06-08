import { cleanup, fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import { launchResponse, taskResponse } from "../test/fixtures";
import TaskInspector from "./TaskInspector.svelte";

describe("TaskInspector", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders Task details, launch summary, graph lists, and journal metadata", async () => {
    const launch = {
      ...launchResponse("00000000-0000-4000-8000-000000000099"),
      status: "FINISHED",
      started_at: "2026-06-05T10:01:00Z",
      finished_at: "2026-06-05T10:08:00Z",
    };
    const onSchedule = vi.fn();
    const onLoadJournal = vi.fn();
    const selectedTask = taskResponse({
      spec_id: "LOAD_RESULTS",
      label: "Load results",
      description: "Persists transformed data",
      status: "SUCCESS",
      latest_launch: launch,
    });

    render(TaskInspector, {
      abortingLaunchId: "",
      directDependencies: [taskResponse({ spec_id: "TRANSFORM_DATA", label: "Transform data" })],
      directDependents: [],
      downstreamImpactTasks: [],
      isLoading: false,
      loadingJournalId: "",
      onAbortLaunch: vi.fn(),
      onClose: vi.fn(),
      onCloseJournal: vi.fn(),
      onLoadJournal,
      onSchedule,
      schedulingTaskId: "",
      selectedJournal: {
        taskLabel: "Load results",
        taskId: "LOAD_RESULTS",
        launch,
        entries: [
          {
            id: "00000000-0000-4000-8000-000000000004",
            message: "Handler started",
            level: "INFO",
            type: "UNCLASSIFIED",
            timestamp: "2026-06-05T16:53:52.956653+00:00",
          },
        ],
      },
      selectedLaunchSummary: { label: "Latest launch", kind: "terminal", launch },
      selectedTask,
    });

    const inspector = screen.getByRole("complementary", { name: "Task inspector" });
    expect(within(inspector).getByRole("heading", { name: "Load results" })).toBeInTheDocument();
    expect(within(inspector).getAllByText("LOAD_RESULTS").length).toBeGreaterThan(0);
    expect(within(inspector).getAllByText(launch.id).length).toBeGreaterThan(0);
    expect(within(inspector).queryByText("By")).not.toBeInTheDocument();
    expect(within(inspector).getByText("Transform data")).toBeInTheDocument();
    expect(within(inspector).getByText("Handler started")).toBeInTheDocument();

    await fireEvent.click(within(inspector).getByRole("button", { name: "Schedule" }));
    await fireEvent.click(within(inspector).getByRole("button", { name: "Open Journal" }));

    expect(onSchedule).toHaveBeenCalledWith(selectedTask);
    expect(onLoadJournal).toHaveBeenCalledWith(selectedTask, launch);
  });

  it("shows Abort Launch only for a current launch", async () => {
    const launch = launchResponse();
    const onAbortLaunch = vi.fn();
    const selectedTask = taskResponse({
      status: "PENDING",
      current_launch: launch,
    });

    render(TaskInspector, {
      abortingLaunchId: "",
      directDependencies: [],
      directDependents: [],
      downstreamImpactTasks: [],
      isLoading: false,
      loadingJournalId: "",
      onAbortLaunch,
      onClose: vi.fn(),
      onCloseJournal: vi.fn(),
      onLoadJournal: vi.fn(),
      onSchedule: vi.fn(),
      schedulingTaskId: "",
      selectedJournal: null,
      selectedLaunchSummary: { label: "Current launch", kind: "active", launch },
      selectedTask,
    });

    await fireEvent.click(screen.getByRole("button", { name: "Abort Launch" }));

    expect(onAbortLaunch).toHaveBeenCalledWith(selectedTask, launch);
  });
});
