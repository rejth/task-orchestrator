const apiKeyStorageKey = "task-orchestrator.api-key";

export function loadApiKey() {
  return localStorage.getItem(apiKeyStorageKey) ?? "";
}

export function saveApiKey(apiKey: string) {
  const trimmed = apiKey.trim();
  if (trimmed.length === 0) {
    localStorage.removeItem(apiKeyStorageKey);
    return "";
  }

  localStorage.setItem(apiKeyStorageKey, trimmed);
  return trimmed;
}

export function clearApiKey() {
  localStorage.removeItem(apiKeyStorageKey);
}
