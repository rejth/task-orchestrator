<script lang="ts">
import { Handle, Position } from "@xyflow/svelte";
import type { TaskGroupNodeData } from "./task-graph";

export type TaskGroupNodeViewData = TaskGroupNodeData & {
  selectionRole: "selected" | "upstream" | "downstream" | "neutral";
};

interface Props {
  data: TaskGroupNodeViewData;
}

let { data }: Props = $props();
</script>

<section
  class={`task-group-node task-group-node-${data.selectionRole}`}
  aria-label={data.label}
  style={`width: ${data.width}px; height: ${data.height}px;`}
>
  <Handle type="target" position={Position.Left} class="task-group-handle" />
  <Handle type="source" position={Position.Right} class="task-group-handle" />

  <div class="task-group-header">
    <strong>{data.label}</strong>
    <span>{data.taskIds.length} tasks</span>
  </div>
</section>

<style>
  .task-group-node {
    position: relative;
    border: 1px solid #cbdde2;
    border-radius: 8px;
    color: #344b55;
    background: rgba(232, 244, 247, 0.54);
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.72),
      0 12px 34px rgba(24, 37, 45, 0.08);
  }

  .task-group-header {
    display: flex;
    gap: 14px;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
  }

  .task-group-header strong {
    min-width: 0;
    color: #243942;
    font-size: 0.92rem;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }

  .task-group-header span {
    flex: 0 0 auto;
    border-radius: 999px;
    padding: 5px 9px;
    color: #4d626c;
    background: rgba(255, 255, 255, 0.78);
    font-size: 0.72rem;
    font-weight: 800;
  }

  .task-group-handle {
    width: 9px;
    height: 9px;
    border: 2px solid #ffffff;
    background: #67818c;
  }
</style>
