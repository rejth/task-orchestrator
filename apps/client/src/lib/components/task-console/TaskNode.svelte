<script lang="ts">
import { Handle, Position } from "@xyflow/svelte";
import type { TaskNodeData } from "$lib/services/task-console/task-graph";

export type TaskNodeViewData = TaskNodeData & {
  displayStatus: (status: string) => string;
  selectionRole: "selected" | "upstream" | "downstream" | "neutral";
};

interface Props {
  data: TaskNodeViewData;
}

let { data }: Props = $props();

let task = $derived(data.task);
</script>

<article class={`task-node task-node-${data.selectionRole}`} data-task-id={task.spec_id} aria-current={data.selectionRole === "selected" ? "true" : undefined}>
  <Handle type="target" position={Position.Left} class="task-node-handle" />

  <div class="task-title-row">
    <strong>{task.label}</strong>
    <span class={`status status-${task.status.toLowerCase().replace(/_/g, "-")}`}>
      {data.displayStatus(task.status)}
    </span>
  </div>
  <span class="task-spec-id">{task.spec_id}</span>

  <p>{task.description}</p>

  <Handle type="source" position={Position.Right} class="task-node-handle" />
</article>

<style>
  .task-node {
    position: relative;
    display: grid;
    gap: 10px;
    min-width: 0;
    border: 1px solid #d6e0e4;
    border-radius: 8px;
    padding: 13px 14px;
    color: #172026;
    background: #ffffff;
    box-shadow: 0 10px 28px rgba(24, 37, 45, 0.1);
  }

  .task-node strong {
    display: block;
  }

  .task-node > p {
    display: -webkit-box;
    margin: 0;
    color: #33464f;
    font-size: 0.9rem;
    line-height: 1.4;
    overflow: hidden;
    -webkit-box-orient: vertical;
  }

  .task-node-handle {
    width: 9px;
    height: 9px;
    border: 2px solid #ffffff;
    background: #1f6f78;
  }

  .task-title-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 14px;
    align-items: start;
  }

  .task-title-row strong {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .task-spec-id {
    display: block;
    color: #61717a;
    font-size: 0.82rem;
    line-height: 1.3;
    overflow-wrap: anywhere;
    word-break: break-word;
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

  @media (max-width: 780px) {
    .task-title-row {
      grid-template-columns: 1fr;
    }

    .status {
      justify-self: start;
    }
  }
</style>
