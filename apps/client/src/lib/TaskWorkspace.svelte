<script lang="ts">
import TaskGraphCanvas from "./TaskGraphCanvas.svelte";
import TaskInspector from "./TaskInspector.svelte";
import type { TaskConsoleController } from "./task-console.svelte";

interface Props {
  controller: TaskConsoleController;
}

let { controller }: Props = $props();
</script>

<section class="workspace" aria-label="Scope Task DAG">
  {#if controller.errorMessage}
    <p class="message error" role="alert">{controller.errorMessage}</p>
  {/if}

  {#if controller.successMessage}
    <p class="message success">{controller.successMessage}</p>
  {/if}

  {#if controller.taskGraph.missingDependencies.length > 0}
    <p class="message warning" role="status">
      Missing dependency endpoints: {controller.missingDependencySummary}
    </p>
  {/if}

  <div class="task-panel" aria-busy={controller.isLoading}>
    <div class="panel-heading">
      <div>
        <p class="eyebrow">Selected Scope</p>
        <h2>{controller.activeScopeId || "None"}</h2>
      </div>
      <div class="panel-badges">
        {#if controller.isLoading}
          <span class="count loading">Loading</span>
        {/if}
        <span class="count">{controller.tasks.length} tasks</span>
      </div>
    </div>

    {#if controller.tasks.length === 0}
      <div class="empty">
        {#if controller.isLoading}
          Loading Task list for this Scope...
        {:else if controller.activeScopeId}
          This Scope does not have any Tasks in its Job.
        {:else}
          Select or initialize a Scope to load its Job Task list.
        {/if}
      </div>
    {:else}
      <div class={`task-console ${controller.selectedTask ? "task-console-with-inspector" : "task-console-graph-only"}`}>
        <TaskGraphCanvas {controller} />

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
      </div>
    {/if}
  </div>
</section>

<style>
  .workspace {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .message {
    margin: 0;
    border-radius: 6px;
    padding: 12px;
    line-height: 1.45;
  }

  .message.error {
    color: #7a261f;
    background: #fde9e7;
  }

  .message.success {
    color: #215339;
    background: #e5f5ec;
  }

  .message.warning {
    color: #6b4700;
    background: #fff1ce;
  }

  .task-panel {
    display: grid;
    gap: 18px;
    border: 1px solid #d9e1e4;
    border-radius: 8px;
    padding: 18px;
    background: #ffffff;
  }

  .panel-heading {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 16px;
  }

  .panel-heading h2 {
    margin: 0;
    color: #172026;
    font-size: 1.05rem;
    line-height: 1.15;
    overflow-wrap: anywhere;
  }

  .panel-badges {
    display: flex;
    flex-wrap: wrap;
    justify-content: end;
    gap: 8px;
  }

  .count {
    flex: 0 0 auto;
    border-radius: 999px;
    padding: 6px 10px;
    color: #37505a;
    background: #eef3f4;
    font-size: 0.86rem;
    font-weight: 700;
  }

  .count.loading {
    color: #5c3c00;
    background: #fff1ce;
  }

  .empty {
    min-height: 220px;
    display: grid;
    place-items: center;
    border: 1px dashed #bdc9ce;
    border-radius: 8px;
    padding: 24px;
    color: #5f7078;
    text-align: center;
  }

  .task-console {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
    align-items: start;
  }

  .task-console-with-inspector {
    grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
  }

  @media (max-width: 1020px) {
    .task-console-with-inspector {
      grid-template-columns: 1fr;
    }
  }
</style>
