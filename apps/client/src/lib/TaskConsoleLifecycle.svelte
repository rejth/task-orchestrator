<script lang="ts">
import type { TaskConsoleController } from "./task-console.svelte";
import { ACTIVE_WORK_POLL_INTERVAL_MS } from "./task-console-view";

interface Props {
  controller: TaskConsoleController;
}

let { controller }: Props = $props();

$effect(() => {
  controller.resetGraphLayout();
});

$effect(() => {
  controller.clearSelectionIfMissing();
});

$effect(() => {
  if (typeof document === "undefined") {
    return;
  }

  const handleVisibilityChange = () => {
    controller.handleDocumentVisibility(document.visibilityState === "visible");
  };

  document.addEventListener("visibilitychange", handleVisibilityChange);

  return () => {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  };
});

$effect(() => {
  if (
    !controller.activeScopeId ||
    !controller.hasActiveWork ||
    !controller.isDocumentVisible ||
    controller.automaticPollingStopped
  ) {
    return;
  }

  const intervalId = window.setInterval(() => {
    void controller.refreshActiveScope({ preserveJournal: true, quiet: true });
  }, ACTIVE_WORK_POLL_INTERVAL_MS);

  return () => {
    window.clearInterval(intervalId);
  };
});
</script>
