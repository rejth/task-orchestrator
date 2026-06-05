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

  it("attaches the API key and parses successful Scope initialization", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ scope_id: scopeId }, 201));

    const client = createApiClient({ apiKey: "secret-key", onUnauthorized: vi.fn() });
    const result = await client.initializeScope(scopeId);

    expect(result.scope_id).toBe(scopeId);
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-Key": "secret-key" }),
      }),
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

    const client = createApiClient({ apiKey: "secret-key", onUnauthorized: vi.fn() });
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

    const client = createApiClient({ apiKey: "secret-key", onUnauthorized: vi.fn() });
    const result = await client.scheduleTask(scopeId, "FETCH_RAW_DATA");

    expect(result).toEqual([
      expect.objectContaining({ spec_id: "FETCH_RAW_DATA", status: "PENDING" }),
    ]);
    expect(fetch).toHaveBeenCalledWith(
      `/api/scopes/${scopeId}/tasks/FETCH_RAW_DATA/schedule`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-Key": "secret-key" }),
      }),
    );
  });

  it("normalizes response validation failures", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ tasks: [{ id: "not-a-uuid" }] }));

    const client = createApiClient({ apiKey: "secret-key", onUnauthorized: vi.fn() });

    await expect(client.getTasks(scopeId)).rejects.toBeInstanceOf(ApiValidationError);
  });

  it("normalizes HTTP errors", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Job was not found" }, 404));

    const client = createApiClient({ apiKey: "secret-key", onUnauthorized: vi.fn() });

    await expect(client.getTasks(scopeId)).rejects.toMatchObject({
      message: "Job was not found",
      status: 404,
    });
  });

  it("notifies the caller before rejecting 401 responses", async () => {
    const onUnauthorized = vi.fn();
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Invalid API key" }, 401));

    const client = createApiClient({ apiKey: "expired-key", onUnauthorized });

    await expect(client.getTasks(scopeId)).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
