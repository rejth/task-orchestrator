<script lang="ts">
import { Handle, Position } from "@xyflow/svelte";
import type { TaskNodeData } from "./task-graph";

export type TaskNodeViewData = TaskNodeData & {
  displayStatus: (status: string) => string;
  selectionRole: "selected" | "upstream" | "downstream" | "neutral";
};

let { data }: { data: TaskNodeViewData } = $props();

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
