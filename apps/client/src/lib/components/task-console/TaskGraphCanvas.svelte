<script lang="ts">
import {
  Background,
  BackgroundVariant,
  Controls,
  type NodeTypes,
  Panel,
  SvelteFlow,
} from "@xyflow/svelte";
import { Button } from "$lib/components/ui/button/index.js";
import type { TaskConsoleController } from "$lib/services/task-console/task-console.svelte";
import {
  TASK_GRAPH_FIT_VIEW_OPTIONS,
  type TaskViewNode,
} from "$lib/services/task-console/task-console-view";
import type { TaskFlowEdge } from "$lib/services/task-console/task-graph";
import TaskGraphAutoFit from "./TaskGraphAutoFit.svelte";
import TaskGroupNode from "./TaskGroupNode.svelte";
import TaskNode from "./TaskNode.svelte";

interface Props {
  controller: TaskConsoleController;
}

const nodeTypes = { task: TaskNode, taskGroup: TaskGroupNode } satisfies NodeTypes;

let { controller }: Props = $props();

let nodes = $state<TaskViewNode[]>([]);
let edges = $state<TaskFlowEdge[]>([]);
let fitKey = $derived(`${nodes.length}:${edges.length}:${nodes.map((node) => node.id).join("|")}`);

$effect(() => {
  nodes = controller.flowNodes;
  edges = controller.flowEdges;
});
</script>

<div class="task-graph" aria-label="Task DAG">
  <SvelteFlow
    bind:nodes
    bind:edges
    {nodeTypes}
    fitView
    fitViewOptions={TASK_GRAPH_FIT_VIEW_OPTIONS}
    nodesConnectable={false}
    nodesDraggable={true}
    deleteKey={null}
    panOnScroll
    minZoom={0.35}
    maxZoom={1.4}
    proOptions={{ hideAttribution: true }}
    onnodeclick={({ node }) => {
      if (node.type === "task") {
        controller.selectTask(node.id);
      }
    }}
  >
    <TaskGraphAutoFit {fitKey} />
    <Background variant={BackgroundVariant.Dots} gap={24} size={1} />
    <Controls fitViewOptions={TASK_GRAPH_FIT_VIEW_OPTIONS} />
    <Panel position="top-right" class="graph-panel">
      <Button type="button" variant="outline" size="sm" onclick={() => controller.resetGraphLayout()}>
        Reset layout
      </Button>
    </Panel>
</SvelteFlow>
</div>

<style>
  .task-graph {
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--muted);
  }

  .task-graph :global(.task-flow-node) {
    width: 300px;
  }

  .task-graph :global(.task-flow-group) {
    pointer-events: all;
  }

  .task-graph :global(.svelte-flow__edge-path) {
    stroke: #7a8b93;
    stroke-width: 2;
  }

  .task-graph :global(.task-flow-edge-muted .svelte-flow__edge-path) {
    stroke: #b9c4c8;
    stroke-width: 1.5;
    opacity: 0.16;
  }

  .task-graph :global(.task-flow-edge-upstream .svelte-flow__edge-path) {
    stroke: #d6aa30;
    stroke-width: 4;
  }

  .task-graph :global(.task-flow-edge-downstream .svelte-flow__edge-path) {
    stroke: #08717c;
    stroke-width: 4;
  }

  .task-graph :global(.svelte-flow__controls) {
    border: 1px solid var(--border);
    box-shadow: var(--shadow-md);
  }

  :global(.task-flow-node-upstream),
  :global(.task-flow-node-downstream),
  :global(.task-flow-group-upstream),
  :global(.task-flow-group-downstream) {
    z-index: 3;
  }

  :global(.task-flow-node-selected),
  :global(.task-flow-group-selected) {
    z-index: 4;
  }

  :global(.task-flow-group-selected .task-group-node) {
    border-color: #08717c;
    background: rgba(232, 251, 253, 0.78);
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.76),
      0 0 0 4px rgba(8, 113, 124, 0.16),
      0 18px 42px rgba(8, 113, 124, 0.16);
  }

  :global(.task-flow-group-upstream .task-group-node) {
    border-color: #d6aa30;
    background: rgba(255, 250, 240, 0.84);
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.76),
      0 0 0 3px rgba(214, 170, 48, 0.16),
      0 14px 32px rgba(155, 106, 0, 0.1);
  }

  :global(.task-flow-group-downstream .task-group-node) {
    border-color: #08717c;
    background: rgba(240, 251, 252, 0.82);
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.76),
      0 0 0 3px rgba(8, 113, 124, 0.14),
      0 14px 32px rgba(8, 113, 124, 0.11);
  }

  :global(.task-flow-group-muted .task-group-node) {
    border-color: #dfe6e8;
    opacity: 0.3;
    filter: grayscale(0.75);
    box-shadow: none;
  }

  :global(.task-flow-node-selected .task-node) {
    border-color: #08717c;
    background: #f7feff;
    box-shadow:
      0 0 0 4px rgba(8, 113, 124, 0.24),
      0 16px 42px rgba(8, 113, 124, 0.22);
  }

  :global(.task-flow-node-upstream .task-node) {
    border-color: #9b6a00;
    background: #fffaf0;
    box-shadow:
      0 0 0 3px rgba(155, 106, 0, 0.2),
      0 12px 30px rgba(155, 106, 0, 0.13);
  }

  :global(.task-flow-node-downstream .task-node) {
    border-color: #08717c;
    background: #f0fbfc;
    box-shadow:
      0 0 0 3px rgba(8, 113, 124, 0.19),
      0 12px 30px rgba(8, 113, 124, 0.14);
  }

  :global(.task-flow-node-muted .task-node) {
    border-color: #dfe6e8;
    opacity: 0.34;
    filter: grayscale(0.75);
    box-shadow: none;
  }

  :global(.task-flow-node-muted .task-node-handle) {
    background: #9aa8ae;
  }

  :global(.graph-panel) {
    display: flex;
    gap: 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 6px;
    background: color-mix(in oklab, var(--card) 94%, transparent);
    box-shadow: var(--shadow-md);
  }
</style>
