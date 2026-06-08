<script lang="ts">
import { Badge } from "$lib/components/ui/badge/index.js";
import { Button } from "$lib/components/ui/button/index.js";
import { Card, CardContent } from "$lib/components/ui/card/index.js";
import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
import { Separator } from "$lib/components/ui/separator/index.js";
import type { Launch, Task } from "$lib/services/task-console/api";
import {
  canSchedule,
  displayStatus,
  formatLaunchTime,
  type LaunchSummary,
  launchTiming,
  type SelectedJournal,
} from "$lib/services/task-console/task-console-view";

interface Props {
  abortingLaunchId: string;
  directDependencies: Task[];
  directDependents: Task[];
  downstreamImpactTasks: Task[];
  isLoading: boolean;
  loadingJournalId: string;
  onAbortLaunch: (task: Task, launch: Launch) => void;
  onClose: () => void;
  onCloseJournal: () => void;
  onLoadJournal: (task: Task, launch: Launch) => void;
  onSchedule: (task: Task) => void;
  schedulingTaskId: string;
  selectedJournal: SelectedJournal | null;
  selectedLaunchSummary: LaunchSummary | undefined;
  selectedTask: Task;
}

let {
  abortingLaunchId,
  directDependencies,
  directDependents,
  downstreamImpactTasks,
  isLoading,
  onAbortLaunch,
  onClose,
  onCloseJournal,
  onLoadJournal,
  onSchedule,
  selectedJournal,
  selectedLaunchSummary,
  selectedTask,
}: Props = $props();

function statusBadgeClass(status: string) {
  switch (status) {
    case "PENDING":
    case "IN_PROGRESS":
      return "bg-amber-100 text-amber-900 hover:bg-amber-100";
    case "SUCCESS":
      return "bg-emerald-100 text-emerald-900 hover:bg-emerald-100";
    case "FAILED":
      return "bg-red-100 text-red-900 hover:bg-red-100";
    case "SKIPPED":
      return "bg-lime-100 text-lime-900 hover:bg-lime-100";
    default:
      return "bg-secondary text-secondary-foreground hover:bg-secondary";
  }
}

function launchCardClass(summary: LaunchSummary | undefined) {
  if (!summary) {
    return "bg-muted/50 text-muted-foreground";
  }

  const status = summary.launch.status;

  if (summary.kind === "active") {
    return "border-amber-500/70 bg-amber-50 text-amber-950 shadow-sm";
  }

  if (status === "SUCCESS" || status === "FINISHED") {
    return "border-emerald-500/70 bg-emerald-50 text-emerald-950 shadow-sm";
  }

  if (status === "FAILED") {
    return "border-red-500/70 bg-red-50 text-red-950 shadow-sm";
  }

  return "border-muted-foreground/30 bg-muted/60";
}
</script>

<ScrollArea class="h-full">
  <aside class="grid min-w-0 gap-5 p-5 pr-6" aria-label="Task inspector">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="mb-1 text-xs font-semibold uppercase text-muted-foreground">Task inspector</p>
        <h3 class="m-0 wrap-break-word text-lg font-semibold leading-tight text-foreground">
          {selectedTask.label}
        </h3>
      </div>
      <Button type="button" variant="ghost" onclick={onClose}>Close</Button>
    </div>

    <Badge class={`w-fit ${statusBadgeClass(selectedTask.status)}`}>
      {displayStatus(selectedTask.status)}
    </Badge>

    <dl class="grid min-w-0 gap-3">
      <div class="grid gap-1">
        <dt class="text-xs font-semibold uppercase text-muted-foreground">Specification ID</dt>
        <dd class="m-0 wrap-break-word text-foreground/80">{selectedTask.spec_id}</dd>
      </div>
      <div class="grid gap-1">
        <dt class="text-xs font-semibold uppercase text-muted-foreground">Task ID</dt>
        <dd class="m-0 wrap-break-word text-foreground/80">{selectedTask.id}</dd>
      </div>
      <div class="grid gap-1">
        <dt class="text-xs font-semibold uppercase text-muted-foreground">Description</dt>
        <dd class="m-0 wrap-break-word leading-relaxed text-foreground/80">{selectedTask.description}</dd>
      </div>
    </dl>

    <section class="grid gap-2" aria-label="Task actions">
      <h4 class="m-0 text-xs font-semibold uppercase text-muted-foreground">Task actions</h4>
      <div class="grid gap-2">
        <Button
          type="button"
          variant="default"
          size="lg"
          class="h-11 border border-primary/20 shadow-sm"
          onclick={() => onSchedule(selectedTask)}
          disabled={isLoading || !canSchedule(selectedTask)}
        >
          Schedule
        </Button>
        {#if selectedLaunchSummary}
          <Button
            type="button"
            variant="secondary"
            size="lg"
            class="h-11 border border-border shadow-sm"
            onclick={() => onLoadJournal(selectedTask, selectedLaunchSummary.launch)}
            disabled={isLoading}
          >
            Open Journal
          </Button>
        {/if}
        {#if selectedTask.current_launch}
          {@const currentLaunch = selectedTask.current_launch}
          <Button
            type="button"
            variant="destructive"
            size="lg"
            class="h-11 border border-destructive/20 shadow-sm"
            onclick={() => onAbortLaunch(selectedTask, currentLaunch)}
            disabled={isLoading}
          >
            Abort Launch
          </Button>
        {/if}
      </div>
    </section>

    <Card size="sm" class={`border-l-4 ${launchCardClass(selectedLaunchSummary)}`}>
      <CardContent class="grid gap-2 px-4">
        {#if selectedLaunchSummary}
          <span class="text-xs font-semibold uppercase text-muted-foreground">{selectedLaunchSummary.label}</span>
          <strong class="wrap-break-word text-foreground">
            {displayStatus(selectedLaunchSummary.launch.status)}
          </strong>
          <span class="wrap-break-word text-sm text-muted-foreground">{selectedLaunchSummary.launch.id}</span>
          {#if selectedLaunchSummary.launch.is_aborted}
            <span class="font-semibold text-destructive">Aborted</span>
          {/if}
          <dl class="mt-1 grid gap-1 text-sm">
            {#each launchTiming(selectedLaunchSummary.launch) as [label, value]}
              <div class="grid grid-cols-[74px_minmax(0,1fr)] gap-2">
                <dt class="font-medium text-muted-foreground">{label}</dt>
                <dd class="m-0 wrap-break-word">{formatLaunchTime(value)}</dd>
              </div>
            {/each}
          </dl>
        {:else}
          <span class="text-xs font-semibold uppercase text-muted-foreground">Launch</span>
          <strong class="text-foreground">None</strong>
          <span>No Launch has been created yet</span>
        {/if}
      </CardContent>
    </Card>

    <section class="grid gap-2" aria-label="Direct dependencies">
      <h4 class="m-0 text-xs font-semibold uppercase text-muted-foreground">Direct dependencies</h4>
      {#if directDependencies.length === 0}
        <p class="m-0 text-sm text-muted-foreground">None</p>
      {:else}
        <ul class="grid gap-2 p-0">
          {#each directDependencies as task}
            <li class="grid gap-1 rounded-md border-l-4 bg-card px-3 py-2 shadow-xs">
              <strong class="wrap-break-word text-sm text-foreground">{task.label}</strong>
              <span class="wrap-break-word text-xs text-muted-foreground">{task.spec_id}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    <section class="grid gap-2" aria-label="Direct dependents">
      <h4 class="m-0 text-xs font-semibold uppercase text-muted-foreground">Direct dependents</h4>
      {#if directDependents.length === 0}
        <p class="m-0 text-sm text-muted-foreground">None</p>
      {:else}
        <ul class="grid gap-2 p-0">
          {#each directDependents as task}
            <li class="grid gap-1 rounded-md border-l-4 bg-card px-3 py-2 shadow-xs">
              <strong class="wrap-break-word text-sm text-foreground">{task.label}</strong>
              <span class="wrap-break-word text-xs text-muted-foreground">{task.spec_id}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    <section class="grid gap-2" aria-label="Downstream impact">
      <h4 class="m-0 text-xs font-semibold uppercase text-muted-foreground">Downstream impact</h4>
      <p class="m-0 text-sm text-muted-foreground">
        {downstreamImpactTasks.length} {downstreamImpactTasks.length === 1 ? "Task" : "Tasks"}
      </p>
      {#if downstreamImpactTasks.length > 0}
        <ul class="grid gap-2 p-0">
          {#each downstreamImpactTasks as task}
            <li class="grid gap-1 rounded-md border-l-4 bg-card px-3 py-2 shadow-xs">
              <strong class="wrap-break-word text-sm text-foreground">{task.label}</strong>
              <span class="wrap-break-word text-xs text-muted-foreground">{task.spec_id}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    {#if selectedJournal}
      <Separator />
      <section class="grid gap-4" aria-label="Launch Journal">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <span class="text-xs font-semibold uppercase text-muted-foreground">Launch Journal</span>
            <strong class="mt-1 block wrap-break-word text-base text-foreground">{selectedJournal.taskLabel}</strong>
          </div>
          <Button type="button" variant="ghost" onclick={onCloseJournal}>Close</Button>
        </div>

        <div class="grid min-w-0 gap-1 text-sm text-muted-foreground">
          <span class="block wrap-break-word">{selectedJournal.taskId}</span>
          <span class="block wrap-break-word">{selectedJournal.launch.id}</span>
        </div>

        {#if selectedJournal.entries.length === 0}
          <p class="m-0 rounded-md border border-dashed p-5 text-center text-muted-foreground">
            This Launch does not have Journal yet.
          </p>
        {:else}
          <ol class="grid gap-2 p-0">
            {#each selectedJournal.entries as entry}
              <li class="grid gap-2 rounded-md border bg-muted/60 p-3">
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                  <strong class="text-foreground">{entry.level}</strong>
                  <span class="text-xs font-semibold uppercase text-muted-foreground">{entry.type}</span>
                  <time class="text-muted-foreground" datetime={entry.timestamp}>
                    {formatLaunchTime(entry.timestamp)}
                  </time>
                </div>
                <p class="m-0 wrap-break-word leading-relaxed text-foreground/80">{entry.message}</p>
              </li>
            {/each}
          </ol>
        {/if}
      </section>
    {/if}
  </aside>
</ScrollArea>
