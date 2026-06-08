<script lang="ts">
import ScopeToolbar from "./lib/components/task-console/ScopeToolbar.svelte";
import TaskConsoleLifecycle from "./lib/components/task-console/TaskConsoleLifecycle.svelte";
import TaskWorkspace from "./lib/components/task-console/TaskWorkspace.svelte";
import { TaskConsoleController } from "./lib/services/task-console/task-console.svelte";

const controller = new TaskConsoleController();
</script>

<svelte:head><title>Task Orchestrator Console</title></svelte:head>
<TaskConsoleLifecycle controller={controller} />

<main class="min-h-screen bg-background pt-[72px] max-sm:pt-28">
	<ScopeToolbar controller={controller} />
	<TaskWorkspace controller={controller} />
</main>
