<script lang="ts">
import type { TaskConsoleController } from "./task-console.svelte";

interface Props {
  controller: TaskConsoleController;
}

let { controller }: Props = $props();
</script>

<section class="toolbar" aria-label="Connection and Scope">
  <div>
    <p class="eyebrow">Task Orchestrator</p>
    <h1>Task DAG console</h1>
  </div>

  <label class="key-field">
    <span>API key</span>
    <input
      bind:value={controller.apiKey}
      type="password"
      autocomplete="off"
      placeholder="Enter server key"
    />
  </label>

  <label>
    <span>Scope ID</span>
    <input
      bind:value={controller.scopeId}
      autocomplete="off"
      placeholder="00000000-0000-4000-8000-000000000000"
    />
  </label>

  <div class="toolbar-actions">
    <button type="button" class="secondary" onclick={() => controller.storeKey()}>Save key</button>
    <button type="button" class="ghost" onclick={() => controller.forgetKey()}>Clear</button>
    <button
      type="button"
      onclick={() => void controller.initializeScope()}
      disabled={controller.isLoading}
    >
      {controller.isLoading ? "Calling API..." : "Initialize Scope"}
    </button>
    <button
      type="button"
      class="secondary"
      onclick={() => void controller.selectScope()}
      disabled={controller.isLoading}
    >
      Select Scope
    </button>
    <button
      type="button"
      class="secondary"
      onclick={() => void controller.refreshActiveScope()}
      disabled={controller.isLoading || !controller.activeScopeId}
    >
      Refresh
    </button>
    <button
      type="button"
      class="danger"
      onclick={() => void controller.stopRun()}
      disabled={controller.isLoading || !controller.activeScopeId}
    >
      {controller.stoppingRun ? "Stopping..." : "Stop Run"}
    </button>
  </div>
</section>

<style>
  .toolbar {
    display: grid;
    grid-template-columns:
      minmax(180px, 0.7fr) minmax(220px, 320px) minmax(260px, 420px)
      minmax(320px, auto);
    gap: 16px;
    align-items: end;
    padding-bottom: 18px;
    border-bottom: 1px solid #d9e1e4;
  }

  h1 {
    margin: 0;
    color: #172026;
    font-size: 1.8rem;
    line-height: 1.15;
  }

  label {
    display: grid;
    gap: 8px;
    color: #3b4b54;
    font-size: 0.92rem;
    font-weight: 600;
  }

  input {
    width: 100%;
    min-height: 42px;
    border: 1px solid #bdc9ce;
    border-radius: 6px;
    padding: 0 12px;
    color: #172026;
    background: #ffffff;
    font: inherit;
  }

  input:focus {
    border-color: #1f6f78;
    outline: 3px solid rgba(31, 111, 120, 0.18);
  }

  .toolbar-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  @media (max-width: 780px) {
    .toolbar {
      grid-template-columns: 1fr;
    }

    .toolbar-actions {
      width: 100%;
    }

    .toolbar-actions button {
      flex: 1 1 150px;
    }
  }
</style>
