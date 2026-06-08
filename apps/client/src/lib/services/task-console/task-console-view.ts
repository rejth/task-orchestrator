import { MarkerType, type Node } from "@xyflow/svelte";
import type { TaskGroupNodeViewData } from "$lib/components/task-console/TaskGroupNode.svelte";
import type { TaskNodeViewData } from "$lib/components/task-console/TaskNode.svelte";
import type { JournalEntry, Launch, Task } from "./api";
import type { MissingDependency, TaskFlowEdge, TaskFlowNode, TaskGraph } from "./task-graph";

export type TaskViewNode =
  | Node<TaskNodeViewData, "task">
  | Node<TaskGroupNodeViewData, "taskGroup">;

export type SelectedJournal = {
  taskLabel: string;
  taskId: string;
  launch: Launch;
  entries: JournalEntry[];
};

export type LaunchSummary = {
  label: "Current launch" | "Latest launch";
  kind: "active" | "terminal";
  launch: Launch;
};

export const ACTIVE_WORK_POLL_INTERVAL_MS = 5_000;
export const TASK_GRAPH_FIT_VIEW_OPTIONS = { includeHiddenNodes: true, padding: 0.22 };

const ACTIVE_TASK_STATUSES = new Set(["PENDING", "IN_PROGRESS"]);

export function hasActiveWork(tasks: Task[]) {
  return tasks.some((task) => ACTIVE_TASK_STATUSES.has(task.status));
}

export function canSchedule(task: Task) {
  return ["NEW", "SUCCESS", "FAILED", "SKIPPED"].includes(task.status);
}

export function displayStatus(status: string) {
  return status;
}

export function formatLaunchTime(value: string | null | undefined) {
  if (!value) {
    return "not recorded";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function missingDependencySummary(missingDependencies: MissingDependency[]) {
  return missingDependencies
    .map(({ taskId, dependencyId }) => `${taskId} depends on ${dependencyId}`)
    .join("; ");
}

export function taskListItems(tasks: Task[], taskIds: string[]) {
  return taskIds
    .map((taskId) => tasks.find((task) => task.spec_id === taskId))
    .filter((task): task is Task => task !== undefined);
}

export function taskLaunchSummary(task: Task): LaunchSummary | undefined {
  if (task.current_launch) {
    return {
      label: "Current launch",
      kind: "active",
      launch: task.current_launch,
    };
  }

  if (task.latest_launch) {
    return {
      label: "Latest launch",
      kind: "terminal",
      launch: task.latest_launch,
    };
  }

  return undefined;
}

export function launchTiming(launch: Launch) {
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

export function buildFlowNodes(
  graph: TaskGraph,
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
) {
  return graph.nodes.map((node) =>
    buildFlowNode(node, selectedTaskId, upstreamTaskIds, downstreamTaskIds),
  ) satisfies TaskViewNode[];
}

function buildFlowNode(
  node: TaskFlowNode,
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
) {
  if (node.type === "taskGroup") {
    return {
      ...node,
      class: taskGroupNodeClass(
        node.data.taskIds,
        selectedTaskId,
        upstreamTaskIds,
        downstreamTaskIds,
      ),
      data: {
        ...node.data,
        selectionRole: taskGroupSelectionRole(
          node.data.taskIds,
          selectedTaskId,
          upstreamTaskIds,
          downstreamTaskIds,
        ),
      },
      domAttributes: {
        "data-testid": `task-group-${node.id}`,
      },
    };
  }

  return {
    ...node,
    class: taskNodeClass(node.id, selectedTaskId, upstreamTaskIds, downstreamTaskIds),
    ariaLabel: `${node.data.task.label} Task`,
    data: {
      ...node.data,
      displayStatus,
      selectionRole: taskSelectionRole(node.id, selectedTaskId, upstreamTaskIds, downstreamTaskIds),
    },
    domAttributes: {
      "data-testid": `task-node-${node.id}`,
    },
  };
}

export function buildFlowEdges(
  graph: TaskGraph,
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
) {
  return graph.edges.map((edge) => {
    const edgeClassName = edgeClass(edge, selectedTaskId, upstreamTaskIds, downstreamTaskIds);

    return {
      ...edge,
      class: edgeClassName,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edgeColor(edgeClassName),
      },
    };
  });
}

export function taskSelectionRole(
  taskId: string,
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
): TaskNodeViewData["selectionRole"] {
  if (!selectedTaskId) {
    return "neutral";
  }

  if (taskId === selectedTaskId) {
    return "selected";
  }

  if (upstreamTaskIds.has(taskId)) {
    return "upstream";
  }

  if (downstreamTaskIds.has(taskId)) {
    return "downstream";
  }

  return "neutral";
}

export function taskNodeClass(
  taskId: string,
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
) {
  const role = taskSelectionRole(taskId, selectedTaskId, upstreamTaskIds, downstreamTaskIds);
  if (role !== "neutral") {
    return `task-flow-node task-flow-node-${role}`;
  }

  return selectedTaskId ? "task-flow-node task-flow-node-muted" : "task-flow-node";
}

export function edgeClass(
  edge: Pick<TaskFlowEdge, "source" | "target" | "data">,
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
) {
  if (!selectedTaskId) {
    return "task-flow-edge";
  }

  const sourceTaskIds = edge.data?.sourceTaskIds ?? [edge.source];
  const targetTaskIds = edge.data?.targetTaskIds ?? [edge.target];
  const isUpstreamEdge =
    targetTaskIds.some(
      (targetTaskId) => targetTaskId === selectedTaskId || upstreamTaskIds.has(targetTaskId),
    ) && sourceTaskIds.some((sourceTaskId) => upstreamTaskIds.has(sourceTaskId));
  const isDownstreamEdge =
    sourceTaskIds.some(
      (sourceTaskId) => sourceTaskId === selectedTaskId || downstreamTaskIds.has(sourceTaskId),
    ) && targetTaskIds.some((targetTaskId) => downstreamTaskIds.has(targetTaskId));

  if (isUpstreamEdge) {
    return "task-flow-edge task-flow-edge-upstream";
  }

  if (isDownstreamEdge) {
    return "task-flow-edge task-flow-edge-downstream";
  }

  return "task-flow-edge task-flow-edge-muted";
}

function taskGroupSelectionRole(
  taskIds: string[],
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
): TaskGroupNodeViewData["selectionRole"] {
  if (!selectedTaskId) {
    return "neutral";
  }

  if (taskIds.includes(selectedTaskId)) {
    return "selected";
  }

  if (taskIds.some((taskId) => upstreamTaskIds.has(taskId))) {
    return "upstream";
  }

  if (taskIds.some((taskId) => downstreamTaskIds.has(taskId))) {
    return "downstream";
  }

  return "neutral";
}

function taskGroupNodeClass(
  taskIds: string[],
  selectedTaskId: string,
  upstreamTaskIds: Set<string>,
  downstreamTaskIds: Set<string>,
) {
  const role = taskGroupSelectionRole(taskIds, selectedTaskId, upstreamTaskIds, downstreamTaskIds);
  if (role !== "neutral") {
    return `task-flow-group task-flow-group-${role}`;
  }

  return selectedTaskId ? "task-flow-group task-flow-group-muted" : "task-flow-group";
}

export function edgeColor(edgeClassName: string) {
  if (edgeClassName.includes("task-flow-edge-upstream")) {
    return "#d6aa30";
  }

  if (edgeClassName.includes("task-flow-edge-downstream")) {
    return "#08717c";
  }

  if (edgeClassName.includes("task-flow-edge-muted")) {
    return "#b9c4c8";
  }

  return "#7a8b93";
}
