<script lang="ts">
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  type Node,
  type NodeTypes,
  SvelteFlow,
} from "@xyflow/svelte";
import {
  ApiError,
  ApiValidationError,
  createApiClient,
  type JournalEntry,
  type Launch,
  type Task,
} from "./lib/api";
import { clearApiKey, loadApiKey, saveApiKey } from "./lib/auth";
import TaskNode, { type TaskNodeViewData } from "./lib/TaskNode.svelte";
import { buildTaskGraph, collectConnectedTaskIds, type TaskFlowEdge } from "./lib/task-graph";

type TaskViewNode = Node<TaskNodeViewData, "task">;

let apiKey = $state(loadApiKey());
let scopeId = $state("");
let activeScopeId = $state("");
let tasks = $state<Task[]>([]);
let errorMessage = $state("");
let successMessage = $state("");
let isLoading = $state(false);
let schedulingTaskId = $state("");
let scheduleResult = $state<Task[]>([]);
let stoppingRun = $state(false);
let abortingLaunchId = $state("");
let loadingJournalId = $state("");
let selectedTaskId = $state("");
let selectedJournal = $state<{
  taskLabel: string;
  taskId: string;
  launch: Launch;
  entries: JournalEntry[];
} | null>(null);

const scopePattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const nodeTypes = { task: TaskNode } satisfies NodeTypes;
let taskGraph = $derived(buildTaskGraph(tasks));
let selectedTask = $derived(tasks.find((task) => task.spec_id === selectedTaskId));
let upstreamTaskIds = $derived(
  selectedTaskId
    ? collectConnectedTaskIds(selectedTaskId, taskGraph.upstreamByTaskId)
    : new Set<string>(),
);
let downstreamTaskIds = $derived(
  selectedTaskId
    ? collectConnectedTaskIds(selectedTaskId, taskGraph.downstreamByTaskId)
    : new Set<string>(),
);
let flowNodes = $state<TaskViewNode[]>([]);
let flowEdges = $state<TaskFlowEdge[]>([]);

$effect(() => {
  flowNodes = taskGraph.nodes.map((node) => ({
    ...node,
    class: taskNodeClass(node.id),
    ariaLabel: taskNodeAriaLabel(node.id, node.data.task.label),
    data: {
      ...node.data,
      displayStatus,
      selectionRole: taskSelectionRole(node.id),
    },
    domAttributes: {
      "data-testid": `task-node-${node.id}`,
    },
  }));
  flowEdges = taskGraph.edges.map((edge) => ({
    ...edge,
    class: edgeClass(edge),
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  }));
});

$effect(() => {
  if (selectedTaskId && !tasks.some((task) => task.spec_id === selectedTaskId)) {
    selectedTaskId = "";
    selectedJournal = null;
  }
});

function storeKey() {
  apiKey = saveApiKey(apiKey);
  successMessage = apiKey.length > 0 ? "API key saved for this browser." : "";
  errorMessage = "";
}

function forgetKey() {
  clearApiKey();
  apiKey = "";
  tasks = [];
  activeScopeId = "";
  scheduleResult = [];
  selectedJournal = null;
  selectedTaskId = "";
  successMessage = "";
  errorMessage = "The API key was cleared.";
}

async function initializeScope() {
  await withApi(async (client, cleanScopeId) => {
    const result = await client.initializeScope(cleanScopeId);
    activeScopeId = result.scope_id;
    tasks = await client.getTasks(result.scope_id);
    scheduleResult = [];
    selectedJournal = null;
    successMessage = `Scope ${result.scope_id} was initialized.`;
  });
}

async function selectScope() {
  await withApi(async (client, cleanScopeId) => {
    tasks = await client.getTasks(cleanScopeId);
    activeScopeId = cleanScopeId;
    scheduleResult = [];
    selectedJournal = null;
    successMessage = `Scope ${cleanScopeId} is selected.`;
  });
}

async function scheduleTask(task: Task) {
  await withApi(
    async (client, cleanScopeId) => {
      schedulingTaskId = task.spec_id;
      const affectedTasks = await client.scheduleTask(cleanScopeId, task.spec_id);
      tasks = await client.getTasks(cleanScopeId);
      activeScopeId = cleanScopeId;
      scheduleResult = affectedTasks;
      successMessage = `${affectedTasks.length} ${affectedTasks.length === 1 ? "Task was" : "Tasks were"} Scheduled from ${task.label}.`;
    },
    {
      explainError: explainScheduleError,
    },
  );
}

async function stopRun() {
  await withApi(
    async (client, cleanScopeId) => {
      stoppingRun = true;
      await client.stopRun(cleanScopeId);
      tasks = await client.getTasks(cleanScopeId);
      activeScopeId = cleanScopeId;
      selectedJournal = null;
      successMessage = `Run for Scope ${cleanScopeId} was stopped.`;
    },
    {
      explainError: explainRunControlError,
    },
  );
}

async function abortLaunch(task: Task, launch: Launch) {
  await withApi(
    async (client, cleanScopeId) => {
      abortingLaunchId = launch.id;
      await client.abortLaunch(cleanScopeId, task.spec_id, launch.id);
      tasks = await client.getTasks(cleanScopeId);
      activeScopeId = cleanScopeId;
      selectedJournal = null;
      successMessage = `Launch ${launch.id} for ${task.label} was aborted.`;
    },
    {
      explainError: explainLaunchOperationError,
    },
  );
}

async function loadJournal(task: Task, launch: Launch) {
  await withApi(
    async (client, cleanScopeId) => {
      loadingJournalId = launch.id;
      const result = await client.getJournal(cleanScopeId, task.spec_id, launch.id);
      activeScopeId = cleanScopeId;
      selectedTaskId = task.spec_id;
      selectedJournal = {
        taskLabel: task.label,
        taskId: task.spec_id,
        launch,
        entries: result.journal,
      };
      successMessage = `Journal for ${task.label} was loaded.`;
    },
    {
      explainError: explainJournalError,
      preserveJournal: true,
    },
  );
}

async function withApi(
  action: (client: ReturnType<typeof createApiClient>, cleanScopeId: string) => Promise<void>,
  options: { explainError?: (error: unknown) => string; preserveJournal?: boolean } = {},
) {
  const cleanKey = saveApiKey(apiKey);
  const cleanScopeId = scopeId.trim();

  errorMessage = "";
  successMessage = "";
  scheduleResult = [];
  if (!options.preserveJournal) {
    selectedJournal = null;
  }

  if (cleanKey.length === 0) {
    errorMessage = "Enter an API key before calling the server.";
    return;
  }

  if (!scopePattern.test(cleanScopeId)) {
    errorMessage = "Enter a Scope ID as a valid UUID.";
    return;
  }

  apiKey = cleanKey;
  isLoading = true;

  const client = createApiClient({
    apiKey: cleanKey,
    onUnauthorized: () => {
      clearApiKey();
      apiKey = "";
    },
  });

  try {
    await action(client, cleanScopeId);
  } catch (error) {
    errorMessage = options.explainError?.(error) ?? explainError(error);
    if (error instanceof ApiError && error.status === 401) {
      tasks = [];
      activeScopeId = "";
    }
    if (error instanceof ApiValidationError) {
      tasks = [];
      activeScopeId = "";
    }
  } finally {
    isLoading = false;
    schedulingTaskId = "";
    stoppingRun = false;
    abortingLaunchId = "";
    loadingJournalId = "";
  }
}

function explainError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "No Scope exists for that ID. Initialize it first or enter another Scope ID.";
    }

    if (error.status === 409) {
      return "A Scope with that ID already exists. Select it instead.";
    }

    return error.message;
  }

  if (error instanceof ApiValidationError) {
    return "The Task list from the server did not match the generated API contract.";
  }

  return "The server response could not be read. Check the API is running and try again.";
}

function explainScheduleError(error: unknown) {
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

function explainRunControlError(error: unknown) {
  if (error instanceof ApiError && error.status === 404) {
    return "No Scope exists for that run. Initialize it first or enter another Scope ID.";
  }

  if (error instanceof ApiValidationError) {
    return "The stop-run response from the server did not match the generated API contract.";
  }

  return explainError(error);
}

function explainLaunchOperationError(error: unknown) {
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

function explainJournalError(error: unknown) {
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

function canSchedule(task: Task) {
  return ["NEW", "SUCCESS", "FAILED", "SKIPPED"].includes(task.status);
}

function displayStatus(status: string) {
  return status;
}

function formatLaunchTime(value: string | null | undefined) {
  if (!value) {
    return "not recorded";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function affectedTaskLabels() {
  return scheduleResult.map((task) => task.label).join(", ");
}

function missingDependencySummary() {
  return taskGraph.missingDependencies
    .map(({ taskId, dependencyId }) => `${taskId} depends on ${dependencyId}`)
    .join("; ");
}

function selectTask({ node }: { node: TaskViewNode }) {
  if (node.id !== selectedTaskId) {
    selectedJournal = null;
  }
  selectedTaskId = node.id;
}

function taskSelectionRole(taskId: string): TaskNodeViewData["selectionRole"] {
  if (!selectedTaskId) {
    return "neutral";
  }

  if (taskId === selectedTaskId) {
    return "selected";
  }

  if (upstreamTaskIds.has(taskId)) {
    return "upstream";
  }

  if (downstreamTaskIds.has(taskId)) {
    return "downstream";
  }

  return "neutral";
}

function taskSelectionLabel(taskId: string) {
  const role = taskSelectionRole(taskId);

  if (role === "selected") {
    return "Selected";
  }

  if (role === "upstream") {
    return "Upstream";
  }

  if (role === "downstream") {
    return "Downstream";
  }

  return "";
}

function taskNodeClass(taskId: string) {
  const role = taskSelectionRole(taskId);
  if (role !== "neutral") {
    return `task-flow-node task-flow-node-${role}`;
  }

  return selectedTaskId ? "task-flow-node task-flow-node-muted" : "task-flow-node";
}

function taskNodeAriaLabel(taskId: string, label: string) {
  const selectionLabel = taskSelectionLabel(taskId);
  return selectionLabel ? `${label} Task, ${selectionLabel}` : `${label} Task`;
}

function edgeClass(edge: TaskFlowEdge) {
  if (!selectedTaskId) {
    return "task-flow-edge";
  }

  const isUpstreamEdge =
    (edge.target === selectedTaskId || upstreamTaskIds.has(edge.target)) &&
    upstreamTaskIds.has(edge.source);
  const isDownstreamEdge =
    (edge.source === selectedTaskId || downstreamTaskIds.has(edge.source)) &&
    downstreamTaskIds.has(edge.target);

  if (isUpstreamEdge) {
    return "task-flow-edge task-flow-edge-upstream";
  }

  if (isDownstreamEdge) {
    return "task-flow-edge task-flow-edge-downstream";
  }

  return "task-flow-edge task-flow-edge-muted";
}

function taskById(taskId: string) {
  return tasks.find((task) => task.spec_id === taskId);
}

function taskListItems(taskIds: string[]) {
  return taskIds
    .map((taskId) => taskById(taskId))
    .filter((task): task is Task => task !== undefined);
}

function downstreamImpactTasks() {
  return taskListItems(Array.from(downstreamTaskIds));
}

function taskLaunchSummary(task: Task) {
  if (task.current_launch) {
    return {
      label: "Current launch",
      kind: "active",
      launch: task.current_launch,
    };
  }

  if (task.latest_launch) {
    return {
      label: "Latest launch",
      kind: "terminal",
      launch: task.latest_launch,
    };
  }

  return undefined;
}

function launchTiming(launch: Launch) {
  return [
    ["Scheduled", launch.scheduled_at],
    ["Started", launch.started_at],
    ["Finished", launch.finished_at],
    ["Failed", launch.failed_at],
    ["Skipped", launch.skipped_at],
  ].filter(
    (entry): entry is [string, JournalEntry["timestamp"]] =>
      typeof entry[1] === "string" && entry[1].length > 0,
  );
}
</script>

<svelte:head>
  <title>Task Orchestrator Console</title>
</svelte:head>

<main class="shell">
  <section class="toolbar" aria-label="Connection and Scope">
    <div>
      <p class="eyebrow">Task Orchestrator</p>
      <h1>Task DAG console</h1>
    </div>

    <label class="key-field">
      <span>API key</span>
      <input bind:value={apiKey} type="password" autocomplete="off" placeholder="Enter server key" />
    </label>

    <label>
      <span>Scope ID</span>
      <input bind:value={scopeId} autocomplete="off" placeholder="00000000-0000-4000-8000-000000000000" />
    </label>

    <div class="toolbar-actions">
      <button type="button" class="secondary" onclick={storeKey}>Save key</button>
      <button type="button" class="ghost" onclick={forgetKey}>Clear</button>
      <button type="button" onclick={initializeScope} disabled={isLoading}>
        {isLoading ? "Calling API..." : "Initialize Scope"}
      </button>
      <button type="button" class="secondary" onclick={selectScope} disabled={isLoading}>
        Select Scope
      </button>
      <button type="button" class="danger" onclick={stopRun} disabled={isLoading || !activeScopeId}>
        {stoppingRun ? "Stopping..." : "Stop Run"}
      </button>
    </div>
  </section>

  <section class="workspace" aria-label="Scope Task DAG">
    {#if errorMessage}
      <p class="message error" role="alert">{errorMessage}</p>
    {/if}

    {#if successMessage}
      <p class="message success">{successMessage}</p>
    {/if}

    {#if taskGraph.missingDependencies.length > 0}
      <p class="message warning" role="status">
        Missing dependency endpoints: {missingDependencySummary()}
      </p>
    {/if}

    {#if scheduleResult.length > 0}
      <div class="schedule-result" aria-live="polite">
        <span>Affected Tasks</span>
        <strong>{affectedTaskLabels()}</strong>
        <p>Schedule accepted. Dispatch will continue through reconciliation if queueing is delayed after commit.</p>
      </div>
    {/if}

    <div class="task-panel">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Selected Scope</p>
          <h2>{activeScopeId || "None"}</h2>
        </div>
        <span class="count">{tasks.length} tasks</span>
      </div>

      {#if tasks.length === 0}
        <div class="empty">
          {#if isLoading}
            Loading Task list for this Scope...
          {:else if activeScopeId}
            This Scope does not have any Tasks in its Job.
          {:else}
            Select or initialize a Scope to load its Job Task list.
          {/if}
        </div>
      {:else}
        <div class="task-console">
          <div class="task-graph" aria-label="Task DAG">
            <SvelteFlow
              bind:nodes={flowNodes}
              bind:edges={flowEdges}
              {nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.22 }}
              nodesConnectable={false}
              deleteKey={null}
              panOnScroll
              minZoom={0.35}
              maxZoom={1.4}
              onnodeclick={selectTask}
            >
              <Background variant={BackgroundVariant.Dots} gap={24} size={1} />
              <Controls />
            </SvelteFlow>
          </div>

          {#if selectedTask}
            {@const directDependencies = taskListItems(taskGraph.upstreamByTaskId.get(selectedTask.spec_id) ?? [])}
            {@const directDependents = taskListItems(taskGraph.downstreamByTaskId.get(selectedTask.spec_id) ?? [])}
            {@const impactTasks = downstreamImpactTasks()}
            {@const selectedLaunchSummary = taskLaunchSummary(selectedTask)}
            {@const selectedJournalForTask = selectedJournal?.taskId === selectedTask.spec_id ? selectedJournal : null}
            <aside class="task-inspector" aria-label="Task inspector">
              <div class="inspector-heading">
                <div>
                  <p class="eyebrow">Task inspector</p>
                  <h3>{selectedTask.label}</h3>
                </div>
                <button type="button" class="ghost" onclick={() => (selectedTaskId = "")}>Close</button>
              </div>

              <span class={`status status-${selectedTask.status.toLowerCase().replace(/_/g, "-")}`}>
                {displayStatus(selectedTask.status)}
              </span>

              <dl class="inspector-details">
                <div>
                  <dt>Specification ID</dt>
                  <dd>{selectedTask.spec_id}</dd>
                </div>
                <div>
                  <dt>Task ID</dt>
                  <dd>{selectedTask.id}</dd>
                </div>
                <div>
                  <dt>Description</dt>
                  <dd>{selectedTask.description}</dd>
                </div>
              </dl>

              <section class="inspector-section task-action-section" aria-label="Task actions">
                <h4>Task actions</h4>
                <div class="inspector-actions">
                  <button
                    type="button"
                    class="secondary"
                    onclick={() => scheduleTask(selectedTask)}
                    disabled={isLoading || !canSchedule(selectedTask)}
                  >
                    {schedulingTaskId === selectedTask.spec_id ? "Scheduling..." : "Schedule"}
                  </button>
                  {#if selectedLaunchSummary}
                    <button
                      type="button"
                      class="ghost"
                      onclick={() => loadJournal(selectedTask, selectedLaunchSummary.launch)}
                      disabled={isLoading}
                    >
                      {loadingJournalId === selectedLaunchSummary.launch.id ? "Loading Journal..." : "Open Journal"}
                    </button>
                  {/if}
                  {#if selectedTask.current_launch}
                    {@const currentLaunch = selectedTask.current_launch}
                    <button
                      type="button"
                      class="danger"
                      onclick={() => abortLaunch(selectedTask, currentLaunch)}
                      disabled={isLoading}
                    >
                      {abortingLaunchId === currentLaunch.id ? "Aborting..." : "Abort Launch"}
                    </button>
                  {/if}
                </div>
              </section>

              <section class={`launch-summary ${selectedLaunchSummary?.kind ?? "none"}`} aria-label="Launch summary">
                {#if selectedLaunchSummary}
                  <span class="launch-label">{selectedLaunchSummary.label}</span>
                  <strong>{displayStatus(selectedLaunchSummary.launch.status)}</strong>
                  <span class="launch-id">{selectedLaunchSummary.launch.id}</span>
                  {#if selectedLaunchSummary.launch.is_aborted}
                    <span class="aborted">Aborted</span>
                  {/if}
                  <dl>
                    {#each launchTiming(selectedLaunchSummary.launch) as [label, value]}
                      <div>
                        <dt>{label}</dt>
                        <dd>{formatLaunchTime(value)}</dd>
                      </div>
                    {/each}
                  </dl>
                {:else}
                  <span class="launch-label">Launch</span>
                  <strong>None</strong>
                  <span>No Schedule or Dispatch has created a Launch yet.</span>
                {/if}
              </section>

              <section class="inspector-section" aria-label="Direct dependencies">
                <h4>Direct dependencies</h4>
                {#if directDependencies.length === 0}
                  <p>None</p>
                {:else}
                  <ul>
                    {#each directDependencies as task}
                      <li>
                        <strong>{task.label}</strong>
                        <span>{task.spec_id}</span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </section>

              <section class="inspector-section" aria-label="Direct dependents">
                <h4>Direct dependents</h4>
                {#if directDependents.length === 0}
                  <p>None</p>
                {:else}
                  <ul>
                    {#each directDependents as task}
                      <li>
                        <strong>{task.label}</strong>
                        <span>{task.spec_id}</span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </section>

              <section class="inspector-section" aria-label="Downstream impact">
                <h4>Downstream impact</h4>
                <p>{impactTasks.length} {impactTasks.length === 1 ? "Task" : "Tasks"}</p>
                {#if impactTasks.length > 0}
                  <ul>
                    {#each impactTasks as task}
                      <li>
                        <strong>{task.label}</strong>
                        <span>{task.spec_id}</span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </section>

              {#if selectedJournalForTask}
                <section class="journal-panel" aria-label="Launch Journal">
                  <div class="journal-heading">
                    <div class="journal-title">
                      <span>Launch Journal</span>
                      <strong>{selectedJournalForTask.taskLabel}</strong>
                    </div>
                    <button type="button" class="ghost" onclick={() => (selectedJournal = null)}>
                      Close
                    </button>
                  </div>
                  <div class="journal-meta">
                    <span>{selectedJournalForTask.taskId}</span>
                    <span>{selectedJournalForTask.launch.id}</span>
                  </div>

                  {#if selectedJournalForTask.entries.length === 0}
                    <p class="journal-empty">This Launch does not have Journal entries yet.</p>
                  {:else}
                    <ol class="journal-entries">
                      {#each selectedJournalForTask.entries as entry}
                        <li>
                          <div class="journal-entry-heading">
                            <strong>{entry.level}</strong>
                            <span>{entry.type}</span>
                            <time datetime={entry.timestamp}>{formatLaunchTime(entry.timestamp)}</time>
                          </div>
                          <p>{entry.message}</p>
                        </li>
                      {/each}
                    </ol>
                  {/if}
                </section>
              {/if}
            </aside>
          {/if}
        </div>
      {/if}
    </div>
  </section>
</main>

<style>
  /* Keeps Svelte/Vite dev HMR on the style-update path for this component. */
</style>
