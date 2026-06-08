import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, launchResponse, scopeId, taskResponse } from "$test/fixtures";
import { TaskConsoleController } from "./task-console.svelte";

describe("TaskConsoleController", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("initializes the demo Scope and stores the loaded Task list", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ scope_id: scopeId }, 201))
      .mockResolvedValueOnce(
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

    await controller.initializeDemoScope();

    expect(controller.activeScopeId).toBe(scopeId);
    expect(controller.tasks).toHaveLength(2);
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      `/api/scopes/${scopeId}`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(2, `/api/scopes/${scopeId}/tasks`, expect.any(Object));
  });

  it("selects the existing demo Scope when initialization returns conflict", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ detail: "Scope already exists" }, 409))
      .mockResolvedValueOnce(jsonResponse({ tasks: [taskResponse()] }));
    const controller = createController();

    await controller.initializeDemoScope();

    expect(controller.activeScopeId).toBe(scopeId);
    expect(controller.tasks).toHaveLength(1);
  });

  it("schedules a Task and refreshes the active demo Scope", async () => {
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
  overrides: Partial<Pick<TaskConsoleController, "activeScopeId" | "tasks">> = {},
) {
  const controller = new TaskConsoleController();
  controller.scopeId = scopeId;
  controller.activeScopeId = overrides.activeScopeId ?? "";
  controller.tasks = overrides.tasks ?? [];
  return controller;
}
