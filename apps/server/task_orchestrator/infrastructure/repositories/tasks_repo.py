from pathlib import Path

import yaml

from task_orchestrator.domain.task import TaskSpecification, TaskSpecificationId

_YAML_PATH = Path(__file__).resolve().parent.parent / "fs" / "task_specifications.yml"


class FsTaskSpecificationsRepo:
    """Loads task specifications from task_specifications.yml at startup."""

    def __init__(self, path: Path = _YAML_PATH) -> None:
        self._specs = self._load(path)

    def all(self) -> list[TaskSpecification]:
        return list(self._specs)

    def find_tasks_by_ids(self, task_ids: list[TaskSpecificationId]) -> list[TaskSpecification]:
        return [spec for spec in self._specs if spec.id in task_ids]

    @staticmethod
    def _load(path: Path) -> list[TaskSpecification]:
        with path.open() as f:
            data = yaml.safe_load(f)

        return [
            TaskSpecification(
                id=TaskSpecificationId(entry["id"]),
                label=entry["label"],
                description=entry["description"],
                depends_on=[TaskSpecificationId(task_id) for task_id in entry.get("depends_on", [])],
            )
            for entry in data
        ]
