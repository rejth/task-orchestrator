<script lang="ts">
import ScopeToolbar from "./lib/ScopeToolbar.svelte";
import TaskConsoleLifecycle from "./lib/TaskConsoleLifecycle.svelte";
import TaskWorkspace from "./lib/TaskWorkspace.svelte";
import { TaskConsoleController } from "./lib/task-console.svelte";

const controller = new TaskConsoleController();
</script>

<svelte:head>
  <title>Task Orchestrator Console</title>
</svelte:head>

<TaskConsoleLifecycle {controller} />

<main class="shell">
  <ScopeToolbar {controller} />
  <TaskWorkspace {controller} />
</main>

<style>
  .shell {
    display: grid;
    gap: 22px;
    width: min(1440px, calc(100% - 32px));
    margin: 0 auto;
    padding: 28px 0;
  }
</style>
