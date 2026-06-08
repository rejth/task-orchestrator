import { ApiError, ApiValidationError, createApiClient, type Launch, type Task } from "./api";
import {
  buildFlowEdges,
  buildFlowNodes,
  hasActiveWork,
  missingDependencySummary,
  type SelectedJournal,
  type TaskViewNode,
  taskLaunchSummary,
  taskListItems,
} from "./task-console-view";
import { buildTaskGraph, collectConnectedTaskIds, type TaskFlowEdge } from "./task-graph";

const scopePattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export const DEMO_SCOPE_ID = "00000000-0000-4000-8000-000000000001";

export class TaskConsoleController {
  scopeId = $state(DEMO_SCOPE_ID);
  activeScopeId = $state("");
  tasks = $state<Task[]>([]);
  errorMessage = $state("");
  successMessage = $state("");
  isLoading = $state(false);
  schedulingTaskId = $state("");
  stoppingRun = $state(false);
  abortingLaunchId = $state("");
  loadingJournalId = $state("");
  selectedTaskId = $state("");
  isDocumentVisible = $state(
    typeof document === "undefined" ? true : document.visibilityState === "visible",
  );
  selectedJournal = $state<SelectedJournal | null>(null);
  flowNodes = $state<TaskViewNode[]>([]);
  flowEdges = $state<TaskFlowEdge[]>([]);
  automaticPollingStopped = $state(false);
  backgroundRefreshInFlight = false;

  taskGraph = $derived(buildTaskGraph(this.tasks));
  selectedTask = $derived(this.tasks.find((task) => task.spec_id === this.selectedTaskId));
  upstreamTaskIds = $derived(
    this.selectedTaskId
      ? collectConnectedTaskIds(this.selectedTaskId, this.taskGraph.upstreamByTaskId)
      : new Set<string>(),
  );
  downstreamTaskIds = $derived(
    this.selectedTaskId
      ? collectConnectedTaskIds(this.selectedTaskId, this.taskGraph.downstreamByTaskId)
      : new Set<string>(),
  );
  hasActiveWork = $derived(hasActiveWork(this.tasks));

  get missingDependencySummary() {
    return missingDependencySummary(this.taskGraph.missingDependencies);
  }

  get directDependencies() {
    if (!this.selectedTask) {
      return [];
    }

    return this.taskListItems(this.taskGraph.upstreamByTaskId.get(this.selectedTask.spec_id) ?? []);
  }

  get directDependents() {
    if (!this.selectedTask) {
      return [];
    }

    return this.taskListItems(
      this.taskGraph.downstreamByTaskId.get(this.selectedTask.spec_id) ?? [],
    );
  }

  get downstreamImpactTasks() {
    return this.taskListItems(Array.from(this.downstreamTaskIds));
  }

  get selectedLaunchSummary() {
    return this.selectedTask ? taskLaunchSummary(this.selectedTask) : undefined;
  }

  get selectedJournalForTask() {
    return this.selectedJournal?.taskId === this.selectedTask?.spec_id
      ? this.selectedJournal
      : null;
  }

  resetGraphLayout() {
    this.flowNodes = buildFlowNodes(
      this.taskGraph,
      this.selectedTaskId,
      this.upstreamTaskIds,
      this.downstreamTaskIds,
    );
    this.flowEdges = buildFlowEdges(
      this.taskGraph,
      this.selectedTaskId,
      this.upstreamTaskIds,
      this.downstreamTaskIds,
    );
  }

  clearSelectionIfMissing() {
    if (this.selectedTaskId && !this.tasks.some((task) => task.spec_id === this.selectedTaskId)) {
      this.selectedTaskId = "";
      this.selectedJournal = null;
    }
  }

  selectTask(taskId: string) {
    if (taskId !== this.selectedTaskId) {
      this.selectedJournal = null;
    }
    this.selectedTaskId = taskId;
  }

  closeInspector() {
    this.selectedTaskId = "";
    this.selectedJournal = null;
  }

  closeJournal() {
    this.selectedJournal = null;
  }

  async initializeDemoScope() {
    await this.withApi(
      async (client, cleanScopeId) => {
        let selectedScopeId = cleanScopeId;
        try {
          const result = await client.initializeScope(cleanScopeId);
          selectedScopeId = result.scope_id;
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 409) {
            throw error;
          }
        }
        this.activeScopeId = selectedScopeId;
        this.tasks = await client.getTasks(selectedScopeId);
        this.selectedJournal = null;
        this.successMessage = "";
      },
      { scopeIdOverride: DEMO_SCOPE_ID },
    );
  }

  async refreshActiveScope(options: { preserveJournal?: boolean; quiet?: boolean } = {}) {
    if (
      !this.activeScopeId ||
      (options.quiet && (this.backgroundRefreshInFlight || this.isLoading))
    ) {
      return;
    }

    if (options.quiet) {
      this.backgroundRefreshInFlight = true;
    }

    try {
      const refreshed = await this.withApi(
        async (client, cleanScopeId) => {
          this.tasks = await client.getTasks(cleanScopeId);
          this.activeScopeId = cleanScopeId;
          if (!options.quiet) {
            this.successMessage = `Scope ${cleanScopeId} was refreshed.`;
          }
        },
        {
          preserveJournal: options.preserveJournal,
          quiet: options.quiet,
          scopeIdOverride: this.activeScopeId,
        },
      );
      if (options.quiet && !refreshed) {
        this.automaticPollingStopped = true;
      }
    } finally {
      this.backgroundRefreshInFlight = false;
    }
  }

  async scheduleTask(task: Task) {
    await this.withApi(
      async (client, cleanScopeId) => {
        this.schedulingTaskId = task.spec_id;
        const affectedTasks = await client.scheduleTask(cleanScopeId, task.spec_id);
        this.tasks = await client.getTasks(cleanScopeId);
        this.activeScopeId = cleanScopeId;
        this.successMessage = `${affectedTasks.length} ${affectedTasks.length === 1 ? "Task was" : "Tasks were"} Scheduled from ${task.label}.`;
      },
      {
        explainError: explainScheduleError,
      },
    );
  }

  async stopRun() {
    await this.withApi(
      async (client, cleanScopeId) => {
        this.stoppingRun = true;
        await client.stopRun(cleanScopeId);
        this.tasks = await client.getTasks(cleanScopeId);
        this.activeScopeId = cleanScopeId;
        this.selectedJournal = null;
        this.successMessage = `Run for Scope ${cleanScopeId} was stopped.`;
      },
      {
        explainError: explainRunControlError,
        scopeIdOverride: this.activeScopeId || this.scopeId,
      },
    );
  }

  async abortLaunch(task: Task, launch: Launch) {
    await this.withApi(
      async (client, cleanScopeId) => {
        this.abortingLaunchId = launch.id;
        await client.abortLaunch(cleanScopeId, task.spec_id, launch.id);
        this.tasks = await client.getTasks(cleanScopeId);
        this.activeScopeId = cleanScopeId;
        this.selectedJournal = null;
        this.successMessage = `Launch ${launch.id} for ${task.label} was aborted.`;
      },
      {
        explainError: explainLaunchOperationError,
      },
    );
  }

  async loadJournal(task: Task, launch: Launch) {
    await this.withApi(
      async (client, cleanScopeId) => {
        this.loadingJournalId = launch.id;
        const result = await client.getJournal(cleanScopeId, task.spec_id, launch.id);
        this.activeScopeId = cleanScopeId;
        this.selectedTaskId = task.spec_id;
        this.selectedJournal = {
          taskLabel: task.label,
          taskId: task.spec_id,
          launch,
          entries: result.journal,
        };
        this.successMessage = `Journal for ${task.label} was loaded.`;
      },
      {
        explainError: explainJournalError,
        preserveJournal: true,
      },
    );
  }

  handleDocumentVisibility(isVisible: boolean) {
    this.isDocumentVisible = isVisible;

    if (isVisible && this.activeScopeId && this.hasActiveWork && !this.automaticPollingStopped) {
      void this.refreshActiveScope({ preserveJournal: true, quiet: true });
    }
  }

  taskListItems(taskIds: string[]) {
    return taskListItems(this.tasks, taskIds);
  }

  async withApi(
    action: (client: ReturnType<typeof createApiClient>, cleanScopeId: string) => Promise<void>,
    options: {
      explainError?: (error: unknown) => string;
      preserveJournal?: boolean;
      quiet?: boolean;
      scopeIdOverride?: string;
    } = {},
  ) {
    const cleanScopeId = (options.scopeIdOverride ?? this.scopeId).trim();

    if (!options.quiet) {
      this.errorMessage = "";
      this.successMessage = "";
    }
    if (!options.preserveJournal) {
      this.selectedJournal = null;
    }

    if (!scopePattern.test(cleanScopeId)) {
      this.errorMessage = "The demo Scope ID is not a valid UUID.";
      return false;
    }

    if (!options.quiet) {
      this.isLoading = true;
    }

    const client = createApiClient();

    try {
      await action(client, cleanScopeId);
      if (options.quiet) {
        this.errorMessage = "";
      } else {
        this.automaticPollingStopped = false;
      }
      return true;
    } catch (error) {
      this.errorMessage = options.explainError?.(error) ?? explainError(error);
      if (error instanceof ApiValidationError) {
        this.tasks = [];
        this.activeScopeId = "";
      }
      return false;
    } finally {
      if (!options.quiet) {
        this.isLoading = false;
      }
      this.schedulingTaskId = "";
      this.stoppingRun = false;
      this.abortingLaunchId = "";
      this.loadingJournalId = "";
    }
  }
}

export function explainError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "The demo Scope was not found. Refresh to recreate it.";
    }

    if (error.status === 409) {
      return "The demo Scope already exists.";
    }

    return error.message;
  }

  if (error instanceof ApiValidationError) {
    return "The Task list from the server did not match the generated API contract.";
  }

  return "The server response could not be read. Check the API is running and try again.";
}

export function explainScheduleError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "That Task or Scope was not found. Refresh the selected Scope and try again.";
    }

    if (error.status === 422) {
      return "That Task cannot be Scheduled in its current state.";
    }
  }

  if (error instanceof ApiValidationError) {
    return "The Schedule response from the server did not match the generated API contract.";
  }

  return explainError(error);
}

export function explainRunControlError(error: unknown) {
  if (error instanceof ApiError && error.status === 404) {
    return "No demo Scope exists for that run. Refresh the page and try again.";
  }

  if (error instanceof ApiValidationError) {
    return "The stop-run response from the server did not match the generated API contract.";
  }

  return explainError(error);
}

export function explainLaunchOperationError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "That Scope, Task, or Launch was not found. Refresh the selected Scope and try again.";
    }

    if (error.status === 422) {
      return "That Launch cannot be aborted in its current state.";
    }
  }

  if (error instanceof ApiValidationError) {
    return "The abort response from the server did not match the generated API contract.";
  }

  return explainError(error);
}

export function explainJournalError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "That Scope, Task, or Launch Journal was not found.";
    }

    if (error.status === 422) {
      return "That Launch ID could not be read.";
    }
  }

  if (error instanceof ApiValidationError) {
    return "The Journal response from the server did not match the generated API contract.";
  }

  return explainError(error);
}
