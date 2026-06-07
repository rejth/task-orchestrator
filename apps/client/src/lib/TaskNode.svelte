<script lang="ts">
import { Handle, Position } from "@xyflow/svelte";
import type { JournalEntry, Launch, Task } from "./api";
import type { TaskNodeData } from "./task-graph";

export type TaskNodeViewData = TaskNodeData & {
  abortingLaunchId: string;
  canSchedule: (task: Task) => boolean;
  displayStatus: (status: string) => string;
  formatLaunchTime: (value: string | null | undefined) => string;
  isLoading: boolean;
  loadingJournalId: string;
  onAbortLaunch: (task: Task, launch: Launch) => void;
  onLoadJournal: (task: Task, launch: Launch) => void;
  onSchedule: (task: Task) => void;
  schedulingTaskId: string;
};

let { data }: { data: TaskNodeViewData } = $props();

let task = $derived(data.task);
let summary = $derived(launchSummary(task));
let currentLaunch = $derived(task.current_launch);

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
    (entry): entry is [string, JournalEntry["timestamp"]] =>
      typeof entry[1] === "string" && entry[1].length > 0,
  );
}
</script>

<article class="task-node" data-task-id={task.spec_id}>
  <Handle type="target" position={Position.Left} class="task-node-handle" />

  <div class="task-title-row">
    <div>
      <strong>{task.label}</strong>
      <span>{task.spec_id}</span>
    </div>
    <span class={`status status-${task.status.toLowerCase().replace(/_/g, "-")}`}>
      {data.displayStatus(task.status)}
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
      onclick={() => data.onSchedule(task)}
      disabled={data.isLoading || !data.canSchedule(task)}
    >
      {data.schedulingTaskId === task.spec_id ? "Scheduling..." : "Schedule"}
    </button>
    {#if summary}
      <button
        type="button"
        class="ghost"
        onclick={() => data.onLoadJournal(task, summary.launch)}
        disabled={data.isLoading}
      >
        {data.loadingJournalId === summary.launch.id ? "Loading Journal..." : "Open Journal"}
      </button>
    {/if}
    {#if currentLaunch}
      <button
        type="button"
        class="danger"
        onclick={() => data.onAbortLaunch(task, currentLaunch)}
        disabled={data.isLoading}
      >
        {data.abortingLaunchId === currentLaunch.id ? "Aborting..." : "Abort Launch"}
      </button>
    {/if}
  </div>

  <aside class={`launch-summary ${summary?.kind ?? "none"}`}>
    {#if summary}
      <span class="launch-label">{summary.label}</span>
      <strong>{data.displayStatus(summary.launch.status)}</strong>
      <span class="launch-id">{summary.launch.id}</span>
      <span>By {summary.launch.scheduled_by}</span>
      {#if summary.launch.is_aborted}
        <span class="aborted">Aborted</span>
      {/if}
      <dl>
        {#each launchTiming(task) as [label, value]}
          <div>
            <dt>{label}</dt>
            <dd>{data.formatLaunchTime(value)}</dd>
          </div>
        {/each}
      </dl>
    {:else}
      <span class="launch-label">Launch</span>
      <strong>None</strong>
      <span>No Schedule or Dispatch has created a Launch yet.</span>
    {/if}
  </aside>

  <Handle type="source" position={Position.Right} class="task-node-handle" />
</article>
