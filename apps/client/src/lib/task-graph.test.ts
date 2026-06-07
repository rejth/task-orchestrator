import { describe, expect, it } from "vitest";
import type { Task } from "./api";
import { buildTaskGraph, collectConnectedTaskIds } from "./task-graph";

describe("buildTaskGraph", () => {
  it("builds an empty graph", () => {
    const graph = buildTaskGraph([]);

    expect(graph.nodes).toEqual([]);
    expect(graph.edges).toEqual([]);
    expect(graph.missingDependencies).toEqual([]);
    expect(graph.upstreamByTaskId.size).toBe(0);
    expect(graph.downstreamByTaskId.size).toBe(0);
  });

  it("lays out a dependency chain from left to right", () => {
    const graph = buildTaskGraph([
      task("FETCH_RAW_DATA"),
      task("TRANSFORM_DATA", ["FETCH_RAW_DATA"]),
      task("LOAD_RESULTS", ["TRANSFORM_DATA"]),
    ]);

    expect(graph.nodes.map((node) => node.id)).toEqual([
      "FETCH_RAW_DATA",
      "TRANSFORM_DATA",
      "LOAD_RESULTS",
    ]);
    expect(graph.edges.map((edge) => [edge.source, edge.target])).toEqual([
      ["FETCH_RAW_DATA", "TRANSFORM_DATA"],
      ["TRANSFORM_DATA", "LOAD_RESULTS"],
    ]);
    expect(graph.edges.every((edge) => edge.type === "default")).toBe(true);
    expect(positionOf(graph, "FETCH_RAW_DATA").x).toBeLessThan(
      positionOf(graph, "TRANSFORM_DATA").x,
    );
    expect(positionOf(graph, "TRANSFORM_DATA").x).toBeLessThan(positionOf(graph, "LOAD_RESULTS").x);
  });

  it("keeps fan-out dependents in the next dependency layer", () => {
    const graph = buildTaskGraph([
      task("FETCH_RAW_DATA"),
      task("TRANSFORM_A", ["FETCH_RAW_DATA"]),
      task("TRANSFORM_B", ["FETCH_RAW_DATA"]),
    ]);

    expect(graph.downstreamByTaskId.get("FETCH_RAW_DATA")).toEqual(["TRANSFORM_A", "TRANSFORM_B"]);
    expect(positionOf(graph, "TRANSFORM_A").x).toBe(positionOf(graph, "TRANSFORM_B").x);
    expect(positionOf(graph, "TRANSFORM_A").y).toBeLessThan(positionOf(graph, "TRANSFORM_B").y);
  });

  it("places fan-in dependents after all present predecessors", () => {
    const graph = buildTaskGraph([
      task("FETCH_A"),
      task("FETCH_B"),
      task("MERGE_RESULTS", ["FETCH_A", "FETCH_B"]),
    ]);

    expect(graph.upstreamByTaskId.get("MERGE_RESULTS")).toEqual(["FETCH_A", "FETCH_B"]);
    expect(graph.edges.map((edge) => [edge.source, edge.target])).toEqual([
      ["FETCH_A", "MERGE_RESULTS"],
      ["FETCH_B", "MERGE_RESULTS"],
    ]);
    expect(positionOf(graph, "FETCH_A").x).toBe(0);
    expect(positionOf(graph, "FETCH_B").x).toBe(0);
    expect(positionOf(graph, "MERGE_RESULTS").x).toBeGreaterThan(0);
  });

  it("omits edges for missing dependencies and reports them", () => {
    const graph = buildTaskGraph([
      task("TRANSFORM_DATA", ["FETCH_RAW_DATA"]),
      task("LOAD_RESULTS", ["TRANSFORM_DATA", "UNKNOWN_EXPORT"]),
    ]);

    expect(graph.edges.map((edge) => [edge.source, edge.target])).toEqual([
      ["TRANSFORM_DATA", "LOAD_RESULTS"],
    ]);
    expect(graph.missingDependencies).toEqual([
      { taskId: "TRANSFORM_DATA", dependencyId: "FETCH_RAW_DATA" },
      { taskId: "LOAD_RESULTS", dependencyId: "UNKNOWN_EXPORT" },
    ]);
    expect(graph.nodes.map((node) => node.id)).toEqual(["TRANSFORM_DATA", "LOAD_RESULTS"]);
  });

  it("collects full upstream and downstream task sets from adjacency maps", () => {
    const graph = buildTaskGraph([
      task("FETCH_RAW_DATA"),
      task("TRANSFORM_A", ["FETCH_RAW_DATA"]),
      task("TRANSFORM_B", ["FETCH_RAW_DATA"]),
      task("MERGE_RESULTS", ["TRANSFORM_A", "TRANSFORM_B"]),
      task("LOAD_RESULTS", ["MERGE_RESULTS"]),
    ]);

    expect(Array.from(collectConnectedTaskIds("MERGE_RESULTS", graph.upstreamByTaskId))).toEqual([
      "TRANSFORM_A",
      "TRANSFORM_B",
      "FETCH_RAW_DATA",
    ]);
    expect(Array.from(collectConnectedTaskIds("FETCH_RAW_DATA", graph.downstreamByTaskId))).toEqual(
      ["TRANSFORM_A", "TRANSFORM_B", "MERGE_RESULTS", "LOAD_RESULTS"],
    );
  });
});

function positionOf(graph: ReturnType<typeof buildTaskGraph>, id: string) {
  const node = graph.nodes.find((candidate) => candidate.id === id);
  if (!node) {
    throw new Error(`Node ${id} was not found`);
  }
  return node.position;
}

function task(specId: string, dependsOn: string[] = []): Task {
  return {
    id: `00000000-0000-4000-8000-${specId.length.toString().padStart(12, "0")}`,
    spec_id: specId,
    label: specId.replace(/_/g, " "),
    description: `${specId} description`,
    depends_on: dependsOn,
    status: "NEW",
    current_launch: null,
    latest_launch: null,
  };
}
