import type { Launch, Task } from "../lib/api";

export const scopeId = "00000000-0000-4000-8000-000000000001";

export function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function taskResponse(overrides: Partial<Task> = {}): Task {
  return {
    id: "00000000-0000-4000-8000-000000000002",
    spec_id: "FETCH_RAW_DATA",
    label: "Fetch raw data",
    description: "Fetches source data",
    depends_on: [],
    status: "NEW",
    current_launch: null,
    latest_launch: null,
    ...overrides,
  };
}

export function launchResponse(id = "00000000-0000-4000-8000-000000000003"): Launch {
  return {
    id,
    scheduled_at: "2026-06-05T10:00:00Z",
    scheduled_by: "secret-key",
    status: "PENDING",
    started_at: null,
    finished_at: null,
    failed_at: null,
    skipped_at: null,
    is_aborted: null,
  };
}
