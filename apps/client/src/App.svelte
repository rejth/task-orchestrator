<script lang="ts">
import { ApiError, ApiValidationError, createApiClient, type Task } from "./lib/api";
import { clearApiKey, loadApiKey, saveApiKey } from "./lib/auth";

let apiKey = $state(loadApiKey());
let scopeId = $state("");
let activeScopeId = $state("");
let tasks = $state<Task[]>([]);
let errorMessage = $state("");
let successMessage = $state("");
let isLoading = $state(false);
let schedulingTaskId = $state("");
let scheduleResult = $state<Task[]>([]);

const scopePattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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
  successMessage = "";
  errorMessage = "The API key was cleared.";
}

async function initializeScope() {
  await withApi(async (client, cleanScopeId) => {
    const result = await client.initializeScope(cleanScopeId);
    activeScopeId = result.scope_id;
    tasks = await client.getTasks(result.scope_id);
    scheduleResult = [];
    successMessage = `Scope ${result.scope_id} was initialized.`;
  });
}

async function selectScope() {
  await withApi(async (client, cleanScopeId) => {
    tasks = await client.getTasks(cleanScopeId);
    activeScopeId = cleanScopeId;
    scheduleResult = [];
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

async function withApi(
  action: (client: ReturnType<typeof createApiClient>, cleanScopeId: string) => Promise<void>,
  options: { explainError?: (error: unknown) => string } = {},
) {
  const cleanKey = saveApiKey(apiKey);
  const cleanScopeId = scopeId.trim();

  errorMessage = "";
  successMessage = "";
  scheduleResult = [];

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

function canSchedule(task: Task) {
  return ["NEW", "SUCCESS", "FAILED", "SKIPPED"].includes(task.status);
}

function displayStatus(status: string) {
  return status.replace(/_/g, " ");
}

function launchSummary(task: Task) {
  if (task.current_launch) {
    return {
      label: "Current Launch",
      kind: "active",
      launch: task.current_launch,
    };
  }

  if (task.latest_launch) {
    return {
      label: "Latest Launch",
      kind: "terminal",
      launch: task.latest_launch,
    };
  }

  return undefined;
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

function launchTiming(task: Task) {
  const launch = task.current_launch ?? task.latest_launch;

  if (!launch) {
    return [];
  }

  return [
    ["Scheduled", launch.scheduled_at],
    ["Started", launch.started_at],
    ["Finished", launch.finished_at],
    ["Failed", launch.failed_at],
    ["Skipped", launch.skipped_at],
  ].filter(
    (entry): entry is [string, string] => typeof entry[1] === "string" && entry[1].length > 0,
  );
}

function affectedTaskLabels() {
  return scheduleResult.map((task) => task.label).join(", ");
}
</script>

<svelte:head>
  <title>Task Orchestrator Console</title>
</svelte:head>

<main class="shell">
  <section class="toolbar" aria-label="Connection">
    <div>
      <p class="eyebrow">Task Orchestrator</p>
      <h1>Operator tracer</h1>
    </div>

    <label class="key-field">
      <span>API key</span>
      <input bind:value={apiKey} type="password" autocomplete="off" placeholder="Enter server key" />
    </label>

    <div class="toolbar-actions">
      <button type="button" class="secondary" onclick={storeKey}>Save key</button>
      <button type="button" class="ghost" onclick={forgetKey}>Clear</button>
    </div>
  </section>

  <section class="workspace" aria-label="Scope tracer">
    <div class="scope-panel">
      <label>
        <span>Scope ID</span>
        <input bind:value={scopeId} autocomplete="off" placeholder="00000000-0000-4000-8000-000000000000" />
      </label>

      <div class="actions">
        <button type="button" onclick={initializeScope} disabled={isLoading}>
          {isLoading ? "Calling API..." : "Initialize Scope"}
        </button>
        <button type="button" class="secondary" onclick={selectScope} disabled={isLoading}>
          Select Scope
        </button>
      </div>

      {#if errorMessage}
        <p class="message error" role="alert">{errorMessage}</p>
      {/if}

      {#if successMessage}
        <p class="message success">{successMessage}</p>
      {/if}

      {#if scheduleResult.length > 0}
        <div class="schedule-result" aria-live="polite">
          <span>Affected Tasks</span>
          <strong>{affectedTaskLabels()}</strong>
          <p>Schedule accepted. Dispatch will continue through reconciliation if queueing is delayed after commit.</p>
        </div>
      {/if}
    </div>

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
        <ul class="tasks" aria-label="Tasks">
          {#each tasks as task}
            {@const summary = launchSummary(task)}
            <li>
              <div class="task-main">
                <div class="task-title-row">
                  <div>
                    <strong>{task.label}</strong>
                    <span>{task.spec_id}</span>
                  </div>
                  <span class={`status status-${task.status.toLowerCase().replace(/_/g, "-")}`}>
                    {displayStatus(task.status)}
                  </span>
                </div>

                <p>{task.description}</p>

                <div class="metadata-row" aria-label={`${task.label} dependencies`}>
                  <span class="metadata-label">Dependencies</span>
                  {#if task.depends_on.length === 0}
                    <span class="dependency empty-dependency">None</span>
                  {:else}
                    {#each task.depends_on as dependency}
                      <span class="dependency">{dependency}</span>
                    {/each}
                  {/if}
                </div>

                <div class="task-actions">
                  <button
                    type="button"
                    class="secondary"
                    onclick={() => scheduleTask(task)}
                    disabled={isLoading || !canSchedule(task)}
                  >
                    {schedulingTaskId === task.spec_id ? "Scheduling..." : "Schedule"}
                  </button>
                </div>
              </div>

              <aside class={`launch-summary ${summary?.kind ?? "none"}`}>
                {#if summary}
                  <span class="launch-label">{summary.label}</span>
                  <strong>{displayStatus(summary.launch.status)}</strong>
                  <span class="launch-id">{summary.launch.id}</span>
                  <span>By {summary.launch.scheduled_by}</span>
                  {#if summary.launch.is_aborted}
                    <span class="aborted">Aborted</span>
                  {/if}
                  <dl>
                    {#each launchTiming(task) as [label, value]}
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
              </aside>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </section>
</main>

<style>
  /* Keeps Svelte/Vite dev HMR on the style-update path for this component. */
</style>
