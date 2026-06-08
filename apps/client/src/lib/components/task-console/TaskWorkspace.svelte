<script lang="ts">
import { Alert } from "$lib/components/ui/alert/index.js";
import { Card, CardContent } from "$lib/components/ui/card/index.js";
import { Sheet, SheetContent } from "$lib/components/ui/sheet/index.js";
import type { TaskConsoleController } from "$lib/services/task-console/task-console.svelte";
import TaskGraphCanvas from "./TaskGraphCanvas.svelte";
import TaskInspector from "./TaskInspector.svelte";

interface Props {
  controller: TaskConsoleController;
}

let { controller }: Props = $props();
</script>

<section
  class="relative h-[calc(100vh-72px)] min-h-[calc(100vh-72px)] overflow-hidden bg-muted max-sm:h-[calc(100vh-112px)] max-sm:min-h-[calc(100vh-112px)]"
  aria-label="Scope Task DAG"
  aria-busy={controller.isLoading}
>
  <div class="pointer-events-none absolute left-4 top-4 z-10 grid w-[min(520px,calc(100%-2rem))] gap-2" aria-live="polite">
    {#if controller.errorMessage}
      <Alert variant="destructive">{controller.errorMessage}</Alert>
    {/if}

    {#if controller.successMessage}
      <Alert class="border-emerald-600/30 text-emerald-800">{controller.successMessage}</Alert>
    {/if}

    {#if controller.taskGraph.missingDependencies.length > 0}
      <Alert class="border-amber-500/40 text-amber-900" role="status">
        Missing dependency endpoints: {controller.missingDependencySummary}
      </Alert>
    {/if}
  </div>

  {#if controller.tasks.length === 0}
    <Card class="absolute left-1/2 top-1/2 w-[min(360px,calc(100%-2rem))] -translate-x-1/2 -translate-y-1/2">
      <CardContent class="py-8 text-center font-medium text-muted-foreground">
        {#if controller.isLoading}
          Loading demo Task DAG...
        {:else}
          The demo Task DAG is not loaded.
        {/if}
      </CardContent>
    </Card>
  {:else}
    <TaskGraphCanvas {controller} />
  {/if}

  <Sheet open={Boolean(controller.selectedTask)} onOpenChange={(open) => !open && controller.closeInspector()}>
    <SheetContent
      class="w-[min(460px,100vw)] gap-0 border-l-2 p-0 shadow-2xl sm:max-w-[460px]"
      side="right"
      showCloseButton={false}
      showOverlay={false}
      interactOutsideBehavior="ignore"
      preventScroll={false}
      trapFocus={false}
    >
      {#if controller.selectedTask}
      <TaskInspector
        abortingLaunchId={controller.abortingLaunchId}
        directDependencies={controller.directDependencies}
        directDependents={controller.directDependents}
        downstreamImpactTasks={controller.downstreamImpactTasks}
        isLoading={controller.isLoading}
        loadingJournalId={controller.loadingJournalId}
        onAbortLaunch={(task, launch) => void controller.abortLaunch(task, launch)}
        onClose={() => controller.closeInspector()}
        onCloseJournal={() => controller.closeJournal()}
        onLoadJournal={(task, launch) => void controller.loadJournal(task, launch)}
        onSchedule={(task) => void controller.scheduleTask(task)}
        schedulingTaskId={controller.schedulingTaskId}
        selectedJournal={controller.selectedJournalForTask}
        selectedLaunchSummary={controller.selectedLaunchSummary}
        selectedTask={controller.selectedTask}
      />
      {/if}
    </SheetContent>
  </Sheet>
</section>
