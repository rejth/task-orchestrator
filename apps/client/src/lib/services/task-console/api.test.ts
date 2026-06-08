import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiValidationError, createApiClient } from "./api";

const scopeId = "00000000-0000-4000-8000-000000000001";

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses successful Scope initialization", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ scope_id: scopeId }, 201));

    const client = createApiClient();
    const result = await client.initializeScope(scopeId);

    expect(result.scope_id).toBe(scopeId);
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("parses generated task-list contracts", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        tasks: [
          {
            id: "00000000-0000-4000-8000-000000000002",
            spec_id: "FETCH_RAW_DATA",
            label: "Fetch raw data",
            description: "Fetches source data",
            depends_on: [],
            status: "NEW",
            current_launch: null,
            latest_launch: {
              id: "00000000-0000-4000-8000-000000000003",
              scheduled_at: "2026-06-05T16:45:52.2208",
              scheduled_by: "secret-key",
              status: "FINISHED",
              started_at: "2026-06-05T16:46:10.410240",
              finished_at: "2026-06-05T16:46:10.999060",
              failed_at: null,
              skipped_at: null,
              is_aborted: null,
            },
          },
        ],
      }),
    );

    const client = createApiClient();
    await expect(client.getTasks(scopeId)).resolves.toEqual([
      expect.objectContaining({ label: "Fetch raw data", status: "NEW" }),
    ]);
  });

  it("posts Schedule requests through the generated response contract", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(
        {
          tasks: [
            {
              id: "00000000-0000-4000-8000-000000000002",
              spec_id: "FETCH_RAW_DATA",
              label: "Fetch raw data",
              description: "Fetches source data",
              depends_on: [],
              status: "PENDING",
              current_launch: {
                id: "00000000-0000-4000-8000-000000000003",
                scheduled_at: "2026-06-05T16:53:52.956653+00:00",
                scheduled_by: "secret-key",
                status: "PENDING",
                started_at: null,
                finished_at: null,
                failed_at: null,
                skipped_at: null,
                is_aborted: null,
              },
              latest_launch: null,
            },
          ],
        },
        202,
      ),
    );

    const client = createApiClient();
    const result = await client.scheduleTask(scopeId, "FETCH_RAW_DATA");

    expect(result).toEqual([
      expect.objectContaining({ spec_id: "FETCH_RAW_DATA", status: "PENDING" }),
    ]);
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/schedule`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("deletes the current run for a Scope", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    const client = createApiClient();

    await expect(client.stopRun(scopeId)).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}/run`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("deletes an individual Launch for abort", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    const client = createApiClient();

    await expect(
      client.abortLaunch(scopeId, "FETCH_RAW_DATA", "00000000-0000-4000-8000-000000000003"),
    ).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/launches/00000000-0000-4000-8000-000000000003`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("parses generated Journal contracts", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        journal: [
          {
            id: "00000000-0000-4000-8000-000000000004",
            message: "Started handler",
            level: "INFO",
            type: "UNCLASSIFIED",
            timestamp: "2026-06-05T16:53:52.956653+00:00",
          },
        ],
      }),
    );

    const client = createApiClient();
    const result = await client.getJournal(
      scopeId,
      "FETCH_RAW_DATA",
      "00000000-0000-4000-8000-000000000003",
    );

    expect(result.journal).toEqual([expect.objectContaining({ message: "Started handler" })]);
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/launches/00000000-0000-4000-8000-000000000003/journal`,
      expect.any(Object),
    );
  });

  it("normalizes response validation failures", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ tasks: [{ id: "not-a-uuid" }] }));

    const client = createApiClient();

    await expect(client.getTasks(scopeId)).rejects.toBeInstanceOf(ApiValidationError);
  });

  it("normalizes HTTP errors", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Job was not found" }, 404));

    const client = createApiClient();

    await expect(client.getTasks(scopeId)).rejects.toMatchObject({
      message: "Job was not found",
      status: 404,
    });
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
