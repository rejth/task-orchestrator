<script lang="ts">
import { useSvelteFlow } from "@xyflow/svelte";
import { tick } from "svelte";
import {
  TASK_GRAPH_FIT_VIEW_OPTIONS,
  type TaskViewNode,
} from "$lib/services/task-console/task-console-view";
import type { TaskFlowEdge } from "$lib/services/task-console/task-graph";

interface Props {
  fitKey: string;
}

let { fitKey }: Props = $props();
let lastFitKey = "";

const { fitView } = useSvelteFlow<TaskViewNode, TaskFlowEdge>();

$effect(() => {
  if (!fitKey || fitKey === lastFitKey) {
    return;
  }

  lastFitKey = fitKey;
  void fitGraph();
});

async function fitGraph() {
  await tick();
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  await fitView(TASK_GRAPH_FIT_VIEW_OPTIONS);
}
</script>
