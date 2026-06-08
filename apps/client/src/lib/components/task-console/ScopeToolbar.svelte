<script lang="ts">
import OctagonXIcon from "@lucide/svelte/icons/octagon-x";
import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
import { Button } from "$lib/components/ui/button/index.js";
import type { TaskConsoleController } from "$lib/services/task-console/task-console.svelte";

interface Props {
  controller: TaskConsoleController;
}

let { controller }: Props = $props();
</script>

<header
  class="fixed inset-x-0 top-0 z-20 flex min-h-[72px] items-center justify-between gap-6 border-b bg-background/95 px-5 py-3 backdrop-blur-sm max-sm:min-h-28 max-sm:flex-col max-sm:items-start max-sm:gap-2.5"
>
  <div class="min-w-0">
    <p class="mb-1 text-xs font-semibold uppercase text-muted-foreground">Task Orchestrator</p>
    <h1 class="m-0 text-xl font-semibold leading-tight text-foreground">Task DAG console</h1>
  </div>

  <nav class="flex shrink-0 items-center gap-2 max-sm:w-full" aria-label="Task run controls">
    <Button
      type="button"
      variant="secondary"
      class="max-sm:flex-1"
      onclick={() => void controller.refreshActiveScope()}
      disabled={controller.isLoading || !controller.activeScopeId}
    >
      <RefreshCwIcon />
      Refresh
    </Button>
    <Button
      type="button"
      variant="destructive"
      class="max-sm:flex-1"
      onclick={() => void controller.stopRun()}
      disabled={controller.isLoading || !controller.activeScopeId}
    >
      <OctagonXIcon />
      {controller.stoppingRun ? "Stopping..." : "Stop Run"}
    </Button>
  </nav>
</header>
