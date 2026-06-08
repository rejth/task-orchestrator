import { describe, expect, it } from "vitest";
import { taskResponse } from "$test/fixtures";
import { buildFlowEdges, buildFlowNodes } from "./task-console-view";
import { buildTaskGraph } from "./task-graph";

describe("task console graph view model", () => {
  it("marks selected, upstream, downstream, and muted graph context", () => {
    const graph = buildTaskGraph([
      taskResponse({ spec_id: "EXTRACT_SOURCE", label: "Extract source" }),
      taskResponse({
        spec_id: "FETCH_RAW_DATA",
        label: "Fetch raw data",
        depends_on: ["EXTRACT_SOURCE"],
      }),
      taskResponse({
        spec_id: "TRANSFORM_DATA",
        label: "Transform data",
        depends_on: ["FETCH_RAW_DATA"],
      }),
      taskResponse({
        spec_id: "LOAD_RESULTS",
        label: "Load results",
        depends_on: ["TRANSFORM_DATA"],
      }),
      taskResponse({ spec_id: "ARCHIVE_UNUSED", label: "Archive unused" }),
    ]);
    const upstreamTaskIds = new Set(["FETCH_RAW_DATA", "EXTRACT_SOURCE"]);
    const downstreamTaskIds = new Set(["LOAD_RESULTS"]);

    const nodes = buildFlowNodes(graph, "TRANSFORM_DATA", upstreamTaskIds, downstreamTaskIds);
    const edges = buildFlowEdges(graph, "TRANSFORM_DATA", upstreamTaskIds, downstreamTaskIds);

    expect(nodes.find((node) => node.id === "TRANSFORM_DATA")).toMatchObject({
      class: "task-flow-node task-flow-node-selected",
      ariaLabel: "Transform data Task",
      data: { selectionRole: "selected" },
    });
    expect(nodes.find((node) => node.id === "FETCH_RAW_DATA")).toMatchObject({
      class: "task-flow-node task-flow-node-upstream",
      data: { selectionRole: "upstream" },
    });
    expect(nodes.find((node) => node.id === "LOAD_RESULTS")).toMatchObject({
      class: "task-flow-node task-flow-node-downstream",
      data: { selectionRole: "downstream" },
    });
    expect(nodes.find((node) => node.id === "ARCHIVE_UNUSED")).toMatchObject({
      class: "task-flow-node task-flow-node-muted",
      data: { selectionRole: "neutral" },
    });
    expect(edges.find((edge) => edge.id === "FETCH_RAW_DATA->TRANSFORM_DATA")).toMatchObject({
      class: "task-flow-edge task-flow-edge-upstream",
      markerEnd: expect.objectContaining({ color: "#d6aa30" }),
    });
    expect(edges.find((edge) => edge.id === "TRANSFORM_DATA->LOAD_RESULTS")).toMatchObject({
      class: "task-flow-edge task-flow-edge-downstream",
      markerEnd: expect.objectContaining({ color: "#08717c" }),
    });
  });

  it("highlights grouped fan-out edges from real task context", () => {
    const graph = buildTaskGraph([
      taskResponse({ spec_id: "FETCH_RAW_DATA", label: "Fetch raw data" }),
      taskResponse({
        spec_id: "TRANSFORM_A",
        label: "Transform A",
        depends_on: ["FETCH_RAW_DATA"],
      }),
      taskResponse({
        spec_id: "TRANSFORM_B",
        label: "Transform B",
        depends_on: ["FETCH_RAW_DATA"],
      }),
      taskResponse({
        spec_id: "TRANSFORM_C",
        label: "Transform C",
        depends_on: ["FETCH_RAW_DATA"],
      }),
    ]);
    const nodes = buildFlowNodes(graph, "TRANSFORM_B", new Set(["FETCH_RAW_DATA"]), new Set());
    const edges = buildFlowEdges(graph, "TRANSFORM_B", new Set(["FETCH_RAW_DATA"]), new Set());

    expect(nodes.find((node) => node.id === "parallel:FETCH_RAW_DATA")).toMatchObject({
      class: "task-flow-group task-flow-group-selected",
      data: { selectionRole: "selected" },
    });
    expect(
      edges.find((edge) => edge.id === "FETCH_RAW_DATA->parallel:FETCH_RAW_DATA"),
    ).toMatchObject({
      class: "task-flow-edge task-flow-edge-upstream",
      markerEnd: expect.objectContaining({ color: "#d6aa30" }),
    });
  });

  it("marks outgoing edges from pending tasks as dashed", () => {
    const graph = buildTaskGraph([
      taskResponse({ spec_id: "FETCH_RAW_DATA", label: "Fetch raw data", status: "PENDING" }),
      taskResponse({
        spec_id: "TRANSFORM_DATA",
        label: "Transform data",
        depends_on: ["FETCH_RAW_DATA"],
      }),
      taskResponse({
        spec_id: "LOAD_RESULTS",
        label: "Load results",
        depends_on: ["TRANSFORM_DATA"],
      }),
    ]);

    const edges = buildFlowEdges(graph, "", new Set(), new Set());

    expect(edges.find((edge) => edge.id === "FETCH_RAW_DATA->TRANSFORM_DATA")).toMatchObject({
      class: "task-flow-edge task-flow-edge-pending-source",
    });
    expect(edges.find((edge) => edge.id === "TRANSFORM_DATA->LOAD_RESULTS")).toMatchObject({
      class: "task-flow-edge",
    });
  });
});
