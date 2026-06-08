<script lang="ts">
import type { Launch, Task } from "./api";
import {
  canSchedule,
  displayStatus,
  formatLaunchTime,
  type LaunchSummary,
  launchTiming,
  type SelectedJournal,
} from "./task-console-view";

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
  loadingJournalId,
  onAbortLaunch,
  onClose,
  onCloseJournal,
  onLoadJournal,
  onSchedule,
  schedulingTaskId,
  selectedJournal,
  selectedLaunchSummary,
  selectedTask,
}: Props = $props();
</script>

<aside class="task-inspector" aria-label="Task inspector">
  <div class="inspector-heading">
    <div>
      <p class="eyebrow">Task inspector</p>
      <h3>{selectedTask.label}</h3>
    </div>
    <button type="button" class="ghost" onclick={onClose}>Close</button>
  </div>

  <span class={`status status-${selectedTask.status.toLowerCase().replace(/_/g, "-")}`}>
    {displayStatus(selectedTask.status)}
  </span>

  <dl class="inspector-details">
    <div>
      <dt>Specification ID</dt>
      <dd>{selectedTask.spec_id}</dd>
    </div>
    <div>
      <dt>Task ID</dt>
      <dd>{selectedTask.id}</dd>
    </div>
    <div>
      <dt>Description</dt>
      <dd>{selectedTask.description}</dd>
    </div>
  </dl>

  <section class="inspector-section task-action-section" aria-label="Task actions">
    <h4>Task actions</h4>
    <div class="inspector-actions">
      <button
        type="button"
        class="secondary"
        onclick={() => onSchedule(selectedTask)}
        disabled={isLoading || !canSchedule(selectedTask)}
      >
        {schedulingTaskId === selectedTask.spec_id ? "Scheduling..." : "Schedule"}
      </button>
      {#if selectedLaunchSummary}
        <button
          type="button"
          class="ghost"
          onclick={() => onLoadJournal(selectedTask, selectedLaunchSummary.launch)}
          disabled={isLoading}
        >
          {loadingJournalId === selectedLaunchSummary.launch.id ? "Loading Journal..." : "Open Journal"}
        </button>
      {/if}
      {#if selectedTask.current_launch}
        {@const currentLaunch = selectedTask.current_launch}
        <button
          type="button"
          class="danger"
          onclick={() => onAbortLaunch(selectedTask, currentLaunch)}
          disabled={isLoading}
        >
          {abortingLaunchId === currentLaunch.id ? "Aborting..." : "Abort Launch"}
        </button>
      {/if}
    </div>
  </section>

  <section class={`launch-summary ${selectedLaunchSummary?.kind ?? "none"}`} aria-label="Launch summary">
    {#if selectedLaunchSummary}
      <span class="launch-label">{selectedLaunchSummary.label}</span>
      <strong>{displayStatus(selectedLaunchSummary.launch.status)}</strong>
      <span class="launch-id">{selectedLaunchSummary.launch.id}</span>
      {#if selectedLaunchSummary.launch.is_aborted}
        <span class="aborted">Aborted</span>
      {/if}
      <dl>
        {#each launchTiming(selectedLaunchSummary.launch) as [label, value]}
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
  </section>

  <section class="inspector-section" aria-label="Direct dependencies">
    <h4>Direct dependencies</h4>
    {#if directDependencies.length === 0}
      <p>None</p>
    {:else}
      <ul>
        {#each directDependencies as task}
          <li>
            <strong>{task.label}</strong>
            <span>{task.spec_id}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <section class="inspector-section" aria-label="Direct dependents">
    <h4>Direct dependents</h4>
    {#if directDependents.length === 0}
      <p>None</p>
    {:else}
      <ul>
        {#each directDependents as task}
          <li>
            <strong>{task.label}</strong>
            <span>{task.spec_id}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <section class="inspector-section" aria-label="Downstream impact">
    <h4>Downstream impact</h4>
    <p>{downstreamImpactTasks.length} {downstreamImpactTasks.length === 1 ? "Task" : "Tasks"}</p>
    {#if downstreamImpactTasks.length > 0}
      <ul>
        {#each downstreamImpactTasks as task}
          <li>
            <strong>{task.label}</strong>
            <span>{task.spec_id}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  {#if selectedJournal}
    <section class="journal-panel" aria-label="Launch Journal">
      <div class="journal-heading">
        <div class="journal-title">
          <span>Launch Journal</span>
          <strong>{selectedJournal.taskLabel}</strong>
        </div>
        <button type="button" class="ghost" onclick={onCloseJournal}>Close</button>
      </div>
      <div class="journal-meta">
        <span>{selectedJournal.taskId}</span>
        <span>{selectedJournal.launch.id}</span>
      </div>

      {#if selectedJournal.entries.length === 0}
        <p class="journal-empty">This Launch does not have Journal entries yet.</p>
      {:else}
        <ol class="journal-entries">
          {#each selectedJournal.entries as entry}
            <li>
              <div class="journal-entry-heading">
                <strong>{entry.level}</strong>
                <span>{entry.type}</span>
                <time datetime={entry.timestamp}>{formatLaunchTime(entry.timestamp)}</time>
              </div>
              <p>{entry.message}</p>
            </li>
          {/each}
        </ol>
      {/if}
    </section>
  {/if}
</aside>

<style>
  .task-inspector {
    display: grid;
    gap: 16px;
    align-content: start;
    min-width: 0;
    width: 100%;
    max-height: clamp(520px, calc(100vh - 230px), 820px);
    border: 1px solid #d9e1e4;
    border-radius: 8px;
    padding: 16px;
    overflow: hidden auto;
    background: #f8fafb;
  }

  .task-inspector > * {
    min-width: 0;
    max-width: 100%;
  }

  .task-inspector > .status {
    justify-self: start;
  }

  .inspector-heading {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 14px;
  }

  .inspector-heading h3 {
    margin: 0;
    color: #172026;
    font-size: 1.05rem;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }

  .inspector-heading button {
    flex: 0 0 auto;
  }

  .status {
    align-self: start;
    border-radius: 999px;
    padding: 6px 10px;
    color: #33464f;
    background: #e9eef0;
    font-size: 0.75rem;
    font-weight: 800;
    white-space: nowrap;
  }

  .status-pending,
  .status-in-progress {
    color: #6b4700;
    background: #fff1ce;
  }

  .status-success {
    color: #215339;
    background: #dff4e8;
  }

  .status-failed {
    color: #7a261f;
    background: #fde2df;
  }

  .status-skipped {
    color: #4a4f27;
    background: #eef1d8;
  }

  .inspector-details {
    display: grid;
    gap: 10px;
    min-width: 0;
    margin: 0;
  }

  .inspector-details div,
  .inspector-section {
    display: grid;
    gap: 6px;
  }

  .inspector-details dt,
  .inspector-section h4 {
    margin: 0;
    color: #6d7d85;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  .inspector-details dd,
  .inspector-section p {
    margin: 0;
    color: #33464f;
    line-height: 1.4;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .inspector-section ul {
    display: grid;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .inspector-section li {
    display: grid;
    gap: 2px;
    border-left: 3px solid #d9e1e4;
    border-radius: 6px;
    padding: 8px 10px;
    background: #ffffff;
  }

  .inspector-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  .inspector-actions button {
    min-width: 0;
    padding: 0 12px;
  }

  .inspector-section strong,
  .inspector-section span {
    overflow-wrap: anywhere;
  }

  .inspector-section strong {
    color: #172026;
    font-size: 0.9rem;
  }

  .inspector-section span {
    color: #61717a;
    font-size: 0.8rem;
  }

  .launch-summary {
    display: grid;
    gap: 6px;
    align-content: start;
    border-left: 3px solid #d9e1e4;
    border-radius: 6px;
    padding: 12px;
    background: #f8fafb;
    color: #3b4b54;
    font-size: 0.82rem;
  }

  .launch-summary.active {
    border-color: #bf7f00;
    background: #fff8e8;
  }

  .launch-summary.terminal {
    border-color: #61717a;
    background: #f3f6f7;
  }

  .launch-summary.none {
    color: #61717a;
  }

  .launch-summary strong {
    color: #172026;
  }

  .launch-summary > span,
  .launch-summary > strong {
    min-width: 0;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .launch-label {
    color: #6d7d85;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  .launch-id {
    display: block;
    color: #61717a;
    font-size: 0.82rem;
    line-height: 1.3;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .launch-summary dl {
    display: grid;
    gap: 5px;
    margin: 4px 0 0;
  }

  .launch-summary dl div {
    display: grid;
    grid-template-columns: 74px minmax(0, 1fr);
    gap: 8px;
  }

  .launch-summary dt {
    color: #6d7d85;
    font-weight: 700;
  }

  .launch-summary dd {
    margin: 0;
    overflow-wrap: anywhere;
  }

  .aborted {
    color: #7a261f;
    font-weight: 800;
  }

  .journal-panel {
    display: grid;
    gap: 14px;
    border-top: 1px solid #d9e1e4;
    padding-top: 18px;
  }

  .journal-heading {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 16px;
  }

  .journal-title {
    min-width: 0;
  }

  .journal-heading span,
  .journal-entry-heading span {
    color: #6d7d85;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  .journal-heading strong {
    display: block;
    margin-top: 4px;
    color: #172026;
    font-size: 1rem;
    overflow-wrap: anywhere;
  }

  .journal-meta {
    display: grid;
    gap: 3px;
    min-width: 0;
  }

  .journal-meta span {
    display: block;
    color: #61717a;
    line-height: 1.25;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .journal-empty {
    margin: 0;
    border: 1px dashed #bdc9ce;
    border-radius: 8px;
    padding: 18px;
    color: #5f7078;
    text-align: center;
  }

  .journal-entries {
    display: grid;
    gap: 10px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .journal-entries li {
    display: grid;
    gap: 8px;
    border: 1px solid #e3e9eb;
    border-radius: 8px;
    padding: 12px;
    background: #f8fafb;
  }

  .journal-entry-heading {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 12px;
    align-items: center;
  }

  .journal-entry-heading strong {
    color: #172026;
  }

  .journal-entry-heading time {
    color: #61717a;
  }

  .journal-entries p {
    margin: 0;
    color: #33464f;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  @media (max-width: 1020px) {
    .task-inspector {
      max-height: 520px;
    }
  }

  @media (max-width: 780px) {
    .journal-heading {
      grid-template-columns: 1fr;
    }

    .task-inspector {
      max-height: 560px;
    }

    .status {
      justify-self: start;
    }
  }
</style>
