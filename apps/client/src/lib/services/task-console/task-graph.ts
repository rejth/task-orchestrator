import { graphlib, layout } from "@dagrejs/dagre";
import { type Edge, type Node, Position } from "@xyflow/svelte";
import type { Task } from "./api";

export type TaskNodeData = {
  task: Task;
};

export type TaskGroupNodeData = {
  label: string;
  taskIds: string[];
  upstreamTaskId: string;
  width: number;
  height: number;
};

export type TaskFlowEdgeData = {
  sourceTaskIds: string[];
  targetTaskIds: string[];
};

export type TaskFlowNode = Node<TaskNodeData, "task"> | Node<TaskGroupNodeData, "taskGroup">;
export type TaskFlowEdge = Edge<TaskFlowEdgeData, "default">;

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

const TASK_NODE_WIDTH = 300;
const TASK_NODE_HEIGHT = 168;
const TASK_NODE_RANK_SEPARATION = 150;
const TASK_NODE_SEPARATION = 70;
const PARALLEL_GROUP_MIN_TASKS = 3;
const PARALLEL_GROUP_COLUMNS = 2;
const PARALLEL_GROUP_PADDING_X = 28;
const PARALLEL_GROUP_PADDING_TOP = 74;
const PARALLEL_GROUP_PADDING_BOTTOM = 28;
const PARALLEL_GROUP_COLUMN_GAP = 32;
const PARALLEL_GROUP_ROW_GAP = 24;

type ParallelTaskGroup = {
  id: string;
  label: string;
  upstreamTaskId: string;
  taskIds: string[];
  childPositions: Map<string, { x: number; y: number }>;
  width: number;
  height: number;
};

type OuterLayoutNode = {
  id: string;
  width: number;
  height: number;
};

type OuterLayoutEdge = {
  source: string;
  target: string;
};

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

  const parallelGroups = detectParallelGroups(tasks, upstreamByTaskId, downstreamByTaskId);
  const parallelGroupByTaskId = mapGroupsByTaskId(parallelGroups);
  const outerLayoutNodes = buildOuterLayoutNodes(tasks, parallelGroups, parallelGroupByTaskId);
  const outerLayoutEdges = buildOuterLayoutEdges(tasks, upstreamByTaskId, parallelGroupByTaskId);
  const layoutByOuterNodeId = buildDagreLayout(outerLayoutNodes, outerLayoutEdges);

  return {
    nodes: buildFlowGraphNodes(tasks, parallelGroups, parallelGroupByTaskId, layoutByOuterNodeId),
    edges: buildFlowGraphEdges(tasks, upstreamByTaskId, parallelGroupByTaskId, parallelGroups),
    upstreamByTaskId,
    downstreamByTaskId,
    missingDependencies,
  };
}

function detectParallelGroups(
  tasks: Task[],
  upstreamByTaskId: Map<string, string[]>,
  downstreamByTaskId: Map<string, string[]>,
) {
  const groups: ParallelTaskGroup[] = [];

  for (const task of tasks) {
    const candidateTaskIds = (downstreamByTaskId.get(task.spec_id) ?? []).filter((taskId) => {
      const upstreamTaskIds = upstreamByTaskId.get(taskId) ?? [];
      return upstreamTaskIds.length === 1 && upstreamTaskIds[0] === task.spec_id;
    });

    if (candidateTaskIds.length < PARALLEL_GROUP_MIN_TASKS) {
      continue;
    }

    groups.push(createParallelGroup(task, candidateTaskIds));
  }

  return groups;
}

function createParallelGroup(upstreamTask: Task, taskIds: string[]): ParallelTaskGroup {
  const columns = Math.min(PARALLEL_GROUP_COLUMNS, taskIds.length);
  const rows = Math.ceil(taskIds.length / columns);
  const width =
    PARALLEL_GROUP_PADDING_X * 2 +
    columns * TASK_NODE_WIDTH +
    (columns - 1) * PARALLEL_GROUP_COLUMN_GAP;
  const height =
    PARALLEL_GROUP_PADDING_TOP +
    PARALLEL_GROUP_PADDING_BOTTOM +
    rows * TASK_NODE_HEIGHT +
    (rows - 1) * PARALLEL_GROUP_ROW_GAP;

  return {
    id: parallelGroupId(upstreamTask.spec_id),
    label: `Parallel tasks after ${upstreamTask.label}`,
    upstreamTaskId: upstreamTask.spec_id,
    taskIds,
    childPositions: new Map(
      taskIds.map((taskId, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);

        return [
          taskId,
          {
            x: PARALLEL_GROUP_PADDING_X + column * (TASK_NODE_WIDTH + PARALLEL_GROUP_COLUMN_GAP),
            y: PARALLEL_GROUP_PADDING_TOP + row * (TASK_NODE_HEIGHT + PARALLEL_GROUP_ROW_GAP),
          },
        ];
      }),
    ),
    width,
    height,
  };
}

function parallelGroupId(upstreamTaskId: string) {
  return `parallel:${upstreamTaskId}`;
}

function mapGroupsByTaskId(parallelGroups: ParallelTaskGroup[]) {
  const groupByTaskId = new Map<string, ParallelTaskGroup>();

  for (const group of parallelGroups) {
    for (const taskId of group.taskIds) {
      groupByTaskId.set(taskId, group);
    }
  }

  return groupByTaskId;
}

function buildOuterLayoutNodes(
  tasks: Task[],
  parallelGroups: ParallelTaskGroup[],
  parallelGroupByTaskId: Map<string, ParallelTaskGroup>,
) {
  return [
    ...parallelGroups.map((group) => ({
      id: group.id,
      width: group.width,
      height: group.height,
    })),
    ...tasks
      .filter((task) => !parallelGroupByTaskId.has(task.spec_id))
      .map((task) => ({
        id: task.spec_id,
        width: TASK_NODE_WIDTH,
        height: TASK_NODE_HEIGHT,
      })),
  ];
}

function buildOuterLayoutEdges(
  tasks: Task[],
  upstreamByTaskId: Map<string, string[]>,
  parallelGroupByTaskId: Map<string, ParallelTaskGroup>,
) {
  const edges = new Map<string, OuterLayoutEdge>();

  for (const task of tasks) {
    const target = parallelGroupByTaskId.get(task.spec_id)?.id ?? task.spec_id;

    for (const dependencyId of upstreamByTaskId.get(task.spec_id) ?? []) {
      const source = parallelGroupByTaskId.get(dependencyId)?.id ?? dependencyId;

      if (source === target) {
        continue;
      }

      edges.set(`${source}->${target}`, { source, target });
    }
  }

  return Array.from(edges.values());
}

function buildFlowGraphNodes(
  tasks: Task[],
  parallelGroups: ParallelTaskGroup[],
  parallelGroupByTaskId: Map<string, ParallelTaskGroup>,
  layoutByOuterNodeId: Map<string, { x: number; y: number }>,
) {
  const groupNodes = parallelGroups.map(
    (group) =>
      ({
        id: group.id,
        type: "taskGroup",
        data: {
          label: group.label,
          taskIds: group.taskIds,
          upstreamTaskId: group.upstreamTaskId,
          width: group.width,
          height: group.height,
        },
        position: layoutByOuterNodeId.get(group.id) ?? { x: 0, y: 0 },
        targetPosition: Position.Left,
        sourcePosition: Position.Right,
        width: group.width,
        height: group.height,
        style: `width: ${group.width}px; height: ${group.height}px;`,
        ariaLabel: group.label,
        zIndex: 0,
      }) satisfies TaskFlowNode,
  );

  const taskNodes = tasks.map((task) => {
    const group = parallelGroupByTaskId.get(task.spec_id);

    return {
      id: task.spec_id,
      type: "task",
      data: { task },
      position: group
        ? (group.childPositions.get(task.spec_id) ?? { x: 0, y: 0 })
        : (layoutByOuterNodeId.get(task.spec_id) ?? { x: 0, y: 0 }),
      parentId: group?.id,
      extent: group ? ("parent" as const) : undefined,
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      ariaLabel: `${task.label} Task`,
      zIndex: group ? 2 : 1,
    } satisfies TaskFlowNode;
  });

  return [...groupNodes, ...taskNodes];
}

function buildFlowGraphEdges(
  tasks: Task[],
  upstreamByTaskId: Map<string, string[]>,
  parallelGroupByTaskId: Map<string, ParallelTaskGroup>,
  parallelGroups: ParallelTaskGroup[],
) {
  const groupsById = new Map(parallelGroups.map((group) => [group.id, group]));
  const edges = new Map<string, TaskFlowEdge>();

  for (const task of tasks) {
    for (const dependencyId of upstreamByTaskId.get(task.spec_id) ?? []) {
      const targetGroup = parallelGroupByTaskId.get(task.spec_id);
      const sourceGroup = parallelGroupByTaskId.get(dependencyId);

      if (targetGroup && sourceGroup?.id === targetGroup.id) {
        continue;
      }

      const source = dependencyId;
      const target = targetGroup?.upstreamTaskId === dependencyId ? targetGroup.id : task.spec_id;
      const targetTaskIds = groupsById.get(target)?.taskIds ?? [task.spec_id];
      const id = `${source}->${target}`;

      edges.set(id, {
        id,
        type: "default" as const,
        source,
        target,
        data: {
          sourceTaskIds: [dependencyId],
          targetTaskIds,
        },
        ariaLabel: `${dependencyId} must finish before ${targetTaskIds.join(", ")}`,
      });
    }
  }

  return Array.from(edges.values());
}

function buildDagreLayout(nodes: OuterLayoutNode[], edges: OuterLayoutEdge[]) {
  const dagreGraph = new graphlib.Graph()
    .setDefaultEdgeLabel(() => ({}))
    .setGraph({
      rankdir: "LR",
      ranksep: TASK_NODE_RANK_SEPARATION,
      nodesep: TASK_NODE_SEPARATION,
      edgesep: 36,
    });

  for (const node of nodes) {
    dagreGraph.setNode(node.id, {
      width: node.width,
      height: node.height,
    });
  }

  for (const edge of edges) {
    dagreGraph.setEdge(edge.source, edge.target);
  }

  layout(dagreGraph);

  const positions = nodes.map((layoutNode) => {
    const node = dagreGraph.node(layoutNode.id);
    return {
      id: layoutNode.id,
      x: node.x - layoutNode.width / 2,
      y: node.y - layoutNode.height / 2,
    };
  });

  const minX = Math.min(0, ...positions.map((position) => position.x));
  const minY = Math.min(0, ...positions.map((position) => position.y));

  return new Map(
    positions.map((position) => [
      position.id,
      {
        x: position.x - minX,
        y: position.y - minY,
      },
    ]),
  );
}

function stableUnique(values: string[]) {
  return Array.from(new Set(values));
}

export function collectConnectedTaskIds(taskId: string, adjacencyByTaskId: Map<string, string[]>) {
  const connectedTaskIds = new Set<string>();
  const queue = [...(adjacencyByTaskId.get(taskId) ?? [])];

  for (let index = 0; index < queue.length; index += 1) {
    const connectedTaskId = queue[index];
    if (!connectedTaskId || connectedTaskIds.has(connectedTaskId)) {
      continue;
    }

    connectedTaskIds.add(connectedTaskId);
    queue.push(...(adjacencyByTaskId.get(connectedTaskId) ?? []));
  }

  return connectedTaskIds;
}
