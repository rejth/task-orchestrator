import { type ZodType, z } from "zod";
import type { TaskListResponse, TaskSchema } from "./api-contract";
import {
  zInitScopeApiScopesScopeIdPostResponse,
  zLaunchSchema,
  zTaskSchema,
} from "./api-contract/zod.gen";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiValidationError extends Error {
  constructor(readonly cause: unknown) {
    super("The server response did not match the expected API contract.");
    this.name = "ApiValidationError";
  }
}

export type Task = TaskSchema;

const localDateTime = z.iso.datetime({ local: true, offset: true });
const launchSchema = zLaunchSchema.extend({
  failed_at: localDateTime.nullish(),
  finished_at: localDateTime.nullish(),
  scheduled_at: localDateTime,
  skipped_at: localDateTime.nullish(),
  started_at: localDateTime.nullish(),
});
const taskSchema = zTaskSchema.extend({
  current_launch: launchSchema.nullish(),
  latest_launch: launchSchema.nullish(),
});
const taskListResponseSchema = z.object({
  tasks: z.array(taskSchema),
}) satisfies ZodType<TaskListResponse>;

type ApiClientOptions = {
  apiKey: string;
  onUnauthorized: () => void;
};

export function createApiClient({ apiKey, onUnauthorized }: ApiClientOptions) {
  async function request<T>(path: string, schema: ZodType<T>, init: RequestInit = {}) {
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
      return parseResponse(schema, undefined);
    }

    return parseResponse(schema, await response.json());
  }

  return {
    async initializeScope(scopeId: string) {
      return request(
        `/api/scopes/${encodeURIComponent(scopeId)}`,
        zInitScopeApiScopesScopeIdPostResponse,
        {
          method: "POST",
        },
      );
    },
    async getTasks(scopeId: string) {
      const result = await request(
        `/api/scopes/${encodeURIComponent(scopeId)}/tasks`,
        taskListResponseSchema,
      );
      return result.tasks;
    },
    async scheduleTask(scopeId: string, taskId: string) {
      const result = await request(
        `/api/scopes/${encodeURIComponent(scopeId)}/tasks/${encodeURIComponent(taskId)}/schedule`,
        taskListResponseSchema,
        {
          method: "POST",
        },
      );
      return result.tasks;
    },
  };
}

function parseResponse<T>(schema: ZodType<T>, payload: unknown) {
  const result = schema.safeParse(payload);
  if (!result.success) {
    throw new ApiValidationError(result.error);
  }
  return result.data;
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
