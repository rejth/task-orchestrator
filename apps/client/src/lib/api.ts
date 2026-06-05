import { z } from "zod";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const taskStatusSchema = z.enum(["NEW", "PENDING", "IN_PROGRESS", "SUCCESS", "FAILED", "SKIPPED"]);

const launchSchema = z.looseObject({
  id: z.string(),
  status: z.string(),
  scheduled_at: z.string(),
  scheduled_by: z.string().nullable().optional(),
  started_at: z.string().optional(),
  finished_at: z.string().optional(),
  failed_at: z.string().optional(),
  skipped_at: z.string().optional(),
  is_aborted: z.boolean().optional(),
});

export const taskSchema = z.object({
  id: z.string(),
  spec_id: z.string(),
  label: z.string(),
  description: z.string(),
  depends_on: z.array(z.string()),
  status: taskStatusSchema,
  current_launch: launchSchema.nullable().optional(),
  latest_launch: launchSchema.nullable().optional(),
});

const tasksResponseSchema = z.object({
  tasks: z.array(taskSchema),
});

const scopeResponseSchema = z.object({
  scope_id: z.string(),
});

export type Task = z.infer<typeof taskSchema>;

type ApiClientOptions = {
  apiKey: string;
  onUnauthorized: () => void;
};

export function createApiClient({ apiKey, onUnauthorized }: ApiClientOptions) {
  async function request(path: string, init: RequestInit = {}) {
    const response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/json",
        "X-API-Key": apiKey,
        ...init.headers,
      },
    });

    if (response.status === 401) {
      onUnauthorized();
      throw new ApiError("The API key was rejected. Enter a valid key to continue.", 401);
    }

    if (!response.ok) {
      throw new ApiError(await readError(response), response.status);
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  }

  return {
    async initializeScope(scopeId: string) {
      const json = await request(`/api/scopes/${encodeURIComponent(scopeId)}`, { method: "POST" });
      return scopeResponseSchema.parse(json);
    },
    async getTasks(scopeId: string) {
      const json = await request(`/api/scopes/${encodeURIComponent(scopeId)}/tasks`);
      return tasksResponseSchema.parse(json).tasks;
    },
  };
}

async function readError(response: Response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    return `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
}
