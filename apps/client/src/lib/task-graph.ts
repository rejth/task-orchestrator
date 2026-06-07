import type { Edge, Node } from "@xyflow/svelte";
import type { Task } from "./api";

export type TaskNodeData = {
  task: Task;
};

export type TaskFlowNode = Node<TaskNodeData, "task">;
export type TaskFlowEdge = Edge<Record<string, never>, "smoothstep">;

export type MissingDependency = {
  taskId: string;
  dependencyId: string;
};

export type TaskGraph = {
  nodes: TaskFlowNode[];
  edges: TaskFlowEdge[];
  upstreamByTaskId: Map<string, string[]>;
  downstreamByTaskId: Map<string, string[]>;
  missingDependencies: MissingDependency[];
};

const COLUMN_GAP = 320;
const ROW_GAP = 160;

export function buildTaskGraph(tasks: Task[]): TaskGraph {
  const taskIds = new Set(tasks.map((task) => task.spec_id));
  const upstreamByTaskId = new Map<string, string[]>();
  const downstreamByTaskId = new Map<string, string[]>();
  const missingDependencies: MissingDependency[] = [];

  for (const task of tasks) {
    upstreamByTaskId.set(task.spec_id, []);
    downstreamByTaskId.set(task.spec_id, []);
  }

  for (const task of tasks) {
    const upstream = upstreamByTaskId.get(task.spec_id) ?? [];

    for (const dependencyId of task.depends_on) {
      if (!taskIds.has(dependencyId)) {
        missingDependencies.push({ taskId: task.spec_id, dependencyId });
        continue;
      }

      upstream.push(dependencyId);
      downstreamByTaskId.get(dependencyId)?.push(task.spec_id);
    }
  }

  for (const [taskId, upstream] of upstreamByTaskId) {
    upstreamByTaskId.set(taskId, stableUnique(upstream));
  }

  for (const [taskId, downstream] of downstreamByTaskId) {
    downstreamByTaskId.set(taskId, stableUnique(downstream));
  }

  const layerByTaskId = calculateDependencyLayers(tasks, upstreamByTaskId, downstreamByTaskId);
  const rowsByLayer = new Map<number, string[]>();

  for (const task of tasks) {
    const layer = layerByTaskId.get(task.spec_id) ?? 0;
    rowsByLayer.set(layer, [...(rowsByLayer.get(layer) ?? []), task.spec_id]);
  }

  const rowByTaskId = new Map<string, number>();
  for (const taskIdsInLayer of rowsByLayer.values()) {
    taskIdsInLayer.forEach((taskId, row) => {
      rowByTaskId.set(taskId, row);
    });
  }

  return {
    nodes: tasks.map((task) => {
      const layer = layerByTaskId.get(task.spec_id) ?? 0;
      const row = rowByTaskId.get(task.spec_id) ?? 0;

      return {
        id: task.spec_id,
        type: "task",
        data: { task },
        position: {
          x: layer * COLUMN_GAP,
          y: row * ROW_GAP,
        },
        ariaLabel: `${task.label} Task`,
      };
    }),
    edges: tasks.flatMap((task) =>
      (upstreamByTaskId.get(task.spec_id) ?? []).map((dependencyId) => ({
        id: `${dependencyId}->${task.spec_id}`,
        type: "smoothstep" as const,
        source: dependencyId,
        target: task.spec_id,
        ariaLabel: `${dependencyId} must finish before ${task.spec_id}`,
      })),
    ),
    upstreamByTaskId,
    downstreamByTaskId,
    missingDependencies,
  };
}

function calculateDependencyLayers(
  tasks: Task[],
  upstreamByTaskId: Map<string, string[]>,
  downstreamByTaskId: Map<string, string[]>,
) {
  const inDegree = new Map<string, number>();
  const layerByTaskId = new Map<string, number>();
  const taskOrder = new Map(tasks.map((task, index) => [task.spec_id, index]));

  for (const task of tasks) {
    const upstream = upstreamByTaskId.get(task.spec_id) ?? [];
    inDegree.set(task.spec_id, upstream.length);
    layerByTaskId.set(task.spec_id, 0);
  }

  const queue = tasks
    .filter((task) => (inDegree.get(task.spec_id) ?? 0) === 0)
    .map((task) => task.spec_id);

  for (let index = 0; index < queue.length; index += 1) {
    const taskId = queue[index];
    if (!taskId) {
      continue;
    }

    for (const downstreamId of downstreamByTaskId.get(taskId) ?? []) {
      layerByTaskId.set(
        downstreamId,
        Math.max(layerByTaskId.get(downstreamId) ?? 0, (layerByTaskId.get(taskId) ?? 0) + 1),
      );

      const nextDegree = (inDegree.get(downstreamId) ?? 0) - 1;
      inDegree.set(downstreamId, nextDegree);

      if (nextDegree === 0) {
        queue.push(downstreamId);
      }
    }

    const sortedTail = queue
      .slice(index + 1)
      .sort((left, right) => (taskOrder.get(left) ?? 0) - (taskOrder.get(right) ?? 0));
    queue.splice(index + 1, sortedTail.length, ...sortedTail);
  }

  return layerByTaskId;
}

function stableUnique(values: string[]) {
  return Array.from(new Set(values));
}
