import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, launchResponse, scopeId, taskResponse } from "../test/fixtures";
import { TaskConsoleController } from "./task-console.svelte";

describe("TaskConsoleController", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("selects a Scope and stores the loaded Task list", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        tasks: [
          taskResponse({ spec_id: "FETCH_RAW_DATA", label: "Fetch raw data" }),
          taskResponse({
            spec_id: "TRANSFORM_DATA",
            label: "Transform data",
            depends_on: ["FETCH_RAW_DATA"],
          }),
        ],
      }),
    );
    const controller = createController();

    await controller.selectScope();

    expect(controller.activeScopeId).toBe(scopeId);
    expect(controller.tasks).toHaveLength(2);
    expect(controller.successMessage).toBe(`Scope ${scopeId} is selected.`);
    expect(fetch).toHaveBeenCalledWith(`/api/scopes/${scopeId}/tasks`, expect.any(Object));
  });

  it("schedules a Task and refreshes the selected Scope", async () => {
    const task = taskResponse({ status: "NEW" });
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ tasks: [taskResponse({ status: "PENDING" })] }, 202))
      .mockResolvedValueOnce(jsonResponse({ tasks: [taskResponse({ status: "PENDING" })] }));
    const controller = createController({ tasks: [task] });

    await controller.scheduleTask(task);

    expect(controller.tasks[0]?.status).toBe("PENDING");
    expect(controller.successMessage).toBe("1 Task was Scheduled from Fetch raw data.");
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/schedule`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(2, `/api/scopes/${scopeId}/tasks`, expect.any(Object));
  });

  it("clears stored credentials and loaded Scope state after unauthorized responses", async () => {
    localStorage.setItem("task-orchestrator.api-key", "expired-key");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Invalid API key" }, 401));
    const controller = createController({ apiKey: "expired-key", tasks: [taskResponse()] });

    await controller.selectScope();

    expect(controller.errorMessage).toContain("The API key was rejected");
    expect(controller.apiKey).toBe("");
    expect(controller.activeScopeId).toBe("");
    expect(controller.tasks).toEqual([]);
    expect(localStorage.getItem("task-orchestrator.api-key")).toBeNull();
  });

  it("stops quiet polling after a background refresh failure", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ detail: "Database is unavailable" }, 500),
    );
    const controller = createController({
      activeScopeId: scopeId,
      tasks: [taskResponse({ status: "PENDING", current_launch: launchResponse() })],
    });

    await controller.refreshActiveScope({ quiet: true, preserveJournal: true });

    expect(controller.automaticPollingStopped).toBe(true);
    expect(controller.errorMessage).toBe("Database is unavailable");
  });
});

function createController(
  overrides: Partial<Pick<TaskConsoleController, "activeScopeId" | "apiKey" | "tasks">> = {},
) {
  const controller = new TaskConsoleController();
  controller.apiKey = overrides.apiKey ?? "secret-key";
  controller.scopeId = scopeId;
  controller.activeScopeId = overrides.activeScopeId ?? "";
  controller.tasks = overrides.tasks ?? [];
  return controller;
}
