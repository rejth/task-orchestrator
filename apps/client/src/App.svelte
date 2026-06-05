<script lang="ts">
import { ApiError, createApiClient, type Task } from "./lib/api";
import { clearApiKey, loadApiKey, saveApiKey } from "./lib/auth";

let apiKey = $state(loadApiKey());
let scopeId = $state("");
let activeScopeId = $state("");
let tasks = $state<Task[]>([]);
let errorMessage = $state("");
let successMessage = $state("");
let isLoading = $state(false);

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
  successMessage = "";
  errorMessage = "The API key was cleared.";
}

async function initializeScope() {
  await withApi(async (client, cleanScopeId) => {
    const result = await client.initializeScope(cleanScopeId);
    activeScopeId = result.scope_id;
    tasks = await client.getTasks(result.scope_id);
    successMessage = `Scope ${result.scope_id} was initialized.`;
  });
}

async function selectScope() {
  await withApi(async (client, cleanScopeId) => {
    tasks = await client.getTasks(cleanScopeId);
    activeScopeId = cleanScopeId;
    successMessage = `Scope ${cleanScopeId} is selected.`;
  });
}

async function withApi(
  action: (client: ReturnType<typeof createApiClient>, cleanScopeId: string) => Promise<void>,
) {
  const cleanKey = saveApiKey(apiKey);
  const cleanScopeId = scopeId.trim();

  errorMessage = "";
  successMessage = "";

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
    errorMessage = explainError(error);
    if (error instanceof ApiError && error.status === 401) {
      tasks = [];
      activeScopeId = "";
    }
  } finally {
    isLoading = false;
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

  return "The server response could not be read. Check the API is running and try again.";
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
        <div class="empty">Initialize or select a Scope to load its task snapshot.</div>
      {:else}
        <ul class="tasks" aria-label="Tasks">
          {#each tasks as task}
            <li>
              <div>
                <strong>{task.label}</strong>
                <span>{task.spec_id}</span>
              </div>
              <span class={`status status-${task.status.toLowerCase().replace(/_/g, "-")}`}>
                {task.status.replace(/_/g, " ")}
              </span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </section>
</main>
