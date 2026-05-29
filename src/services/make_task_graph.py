from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from typing import Callable

from src.domain.scoped_task import ScheduledScopedTask
from src.domain.task import TaskSpecificationId


@dataclass(frozen=True)
class LeafTask:
    value: ScheduledScopedTask


@dataclass(frozen=True)
class ParallelTasks:
    value: list[LeafTask | SequentialTasks]


@dataclass(frozen=True)
class SequentialTasks:
    values: list[LeafTask | ParallelTasks]


@dataclass(frozen=True)
class TaskVertex:
    value: ScheduledScopedTask
    dependent: list[ScheduledScopedTask]

    @property
    def spec_id(self) -> TaskSpecificationId:
        return self.value.spec_id


TaskGraphDependencies = dict[TaskSpecificationId, TaskVertex]


class TaskGraph:
    def __init__(self, tasks_sequence: list[ScheduledScopedTask]):
        self.tasks = tasks_sequence
        self.task_dependencies = self._build_graph_dependencies(tasks=self.tasks)
        self.sorted_tasks: list[ScheduledScopedTask] = []
        self.visited: set[TaskSpecificationId] = set()

    def make_graph(self) -> SequentialTasks:
        return self._build_graph()

    def _build_graph(self) -> SequentialTasks:
        tasks: list[LeafTask | ParallelTasks] = []
        self.sorted_tasks = self._topological_sort()
        root_tasks = self._find_root_tasks(tasks=self.sorted_tasks)
        task_dependencies = self._build_graph_dependencies(tasks=self.sorted_tasks)

        if len(root_tasks) == 1:
            tasks.append(LeafTask(value=root_tasks[0]))
            root_ids = {task.spec_id for task in root_tasks}
            without_root = [t for t in self.sorted_tasks if t.spec_id not in root_ids]

            def _filter_with_root(parent_count: int, child_count: int) -> bool:
                return parent_count > 1 and child_count >= 1

            tasks_groups = self._find_all_parallel_groups(without_root, _filter_with_root)
        else:
            def _filter_without_root(_parent_count: int, child_count: int) -> bool:
                return child_count >= 1

            tasks_groups = self._find_all_parallel_groups(self.sorted_tasks, _filter_without_root)

        if not tasks_groups:
            task_sequence = self._build_task_sequence(task_dependencies, [])
            return SequentialTasks(values=[*tasks, *task_sequence.values])

        group_parents: list[ScheduledScopedTask] = []
        for _, task_list in tasks_groups:
            group_parents += task_list

        task_sequence = self._build_task_sequence(task_dependencies, group_parents)
        tasks += task_sequence.values

        for _, task_list in tasks_groups:
            task_group = self._build_task_group(task_dependencies, task_list, group_parents)
            if task_group.value:
                tasks.append(task_group)

        return SequentialTasks(values=tasks)

    def _topological_sort(self) -> list[ScheduledScopedTask]:
        queue: Queue[TaskSpecificationId] = Queue()
        sorted_tasks: list[ScheduledScopedTask] = []
        in_degree: dict[TaskSpecificationId, int] = {}

        for spec_id, task in self.task_dependencies.items():
            in_degree[spec_id] = in_degree.get(spec_id, 0)
            for child in task.dependent:
                in_degree[child.spec_id] = in_degree.get(child.spec_id, 0) + 1

        for spec_id, degree in in_degree.items():
            if degree == 0:
                queue.put(spec_id)

        while not queue.empty():
            spec_id = queue.get()
            task = self.task_dependencies[spec_id]
            sorted_tasks.append(task.value)
            for child in task.dependent:
                in_degree[child.spec_id] -= 1
                if in_degree[child.spec_id] == 0:
                    queue.put(child.spec_id)

        return sorted_tasks

    def _build_task_sequence(
        self,
        graph: TaskGraphDependencies,
        tasks_to_exclude: list[ScheduledScopedTask]
    ) -> SequentialTasks:
        tasks = []

        for spec_id, task in graph.items():
            # Restrict to dependents visible in the current (sub)graph only.
            # task.dependent is built from the full scheduled task set and can
            # reference tasks that were excluded from this sub-traversal.
            dependent_tasks = [dependent for dependent in task.dependent if dependent.spec_id in graph]
            if all(item in tasks_to_exclude for item in dependent_tasks):
                return SequentialTasks(values=tasks)
            if spec_id in self.visited and self._all_visited(dependent_tasks):
                return SequentialTasks(values=tasks)

            tasks_ahead = [graph[item.spec_id].dependent for item in dependent_tasks]
            spec_ids = [[item.spec_id for item in ta] for ta in tasks_ahead]
            is_equal = all(set(spec_ids[0]) == set(ids) for ids in spec_ids)

            if len(dependent_tasks) > 1 and not is_equal:
                task_group = self._build_task_group(graph, dependent_tasks, tasks_to_exclude)
                tasks.append(task_group)
            elif len(dependent_tasks) > 1 and not self._all_visited(dependent_tasks):
                self._visit_all_nodes(dependent_tasks)
                tasks.append(ParallelTasks(value=[LeafTask(value=item) for item in dependent_tasks]))
            elif len(dependent_tasks) == 1 and not self._all_visited(dependent_tasks):
                t = dependent_tasks[0]
                self.visited.add(t.spec_id)
                tasks.append(LeafTask(value=t))
            elif task.spec_id not in self.visited:
                self.visited.add(task.spec_id)
                tasks.append(LeafTask(value=task.value))

        return SequentialTasks(values=tasks)

    def _build_task_group(
        self,
        graph: TaskGraphDependencies,
        tasks: list[ScheduledScopedTask],
        tasks_to_exclude: list[ScheduledScopedTask],
    ) -> ParallelTasks:
        task_group: list[LeafTask | SequentialTasks] = []

        for task in tasks:
            current_task = graph[task.spec_id]

            if task.spec_id in self.visited:
                return ParallelTasks(value=task_group)

            traversal = self._traverse_graph(current_task, tasks_to_exclude)
            sub_graph = {item.spec_id: item for item in traversal}
            self.visited.add(task.spec_id)

            if len(traversal) > 1:
                inner = self._build_task_sequence(sub_graph, tasks_to_exclude).values
                task_group.append(SequentialTasks(values=[LeafTask(value=task), *inner]))
            elif traversal:
                task_group.append(LeafTask(value=task))

        return ParallelTasks(value=task_group)

    @staticmethod
    def _build_graph_dependencies(tasks: list[ScheduledScopedTask]) -> TaskGraphDependencies:
        deps: TaskGraphDependencies = {}

        for task in tasks:
            spec_id = task.spec_id
            dependent = [item for item in tasks if spec_id in item.specification.depends_on]
            deps[spec_id] = TaskVertex(value=task, dependent=dependent)

        return deps

    def _all_visited(self, tasks: list[ScheduledScopedTask]) -> bool:
        return all(t.spec_id in self.visited for t in tasks)

    def _visit_all_nodes(self, tasks: list[ScheduledScopedTask]) -> None:
        self.visited.update(t.spec_id for t in tasks)

    def _traverse_graph(self, root: TaskVertex, nodes_to_exclude: list[ScheduledScopedTask]) -> list[TaskVertex]:
        queue: Queue[TaskVertex] = Queue()
        visited: set[TaskSpecificationId] = set()
        traversal: list[TaskVertex] = []

        def visit_node(node: TaskVertex) -> None:
            visited.add(node.spec_id)
            traversal.append(node)
            queue.put(node)

        visit_node(root)
        while not queue.empty():
            task = queue.get()
            for item in task.dependent:
                if item in nodes_to_exclude:
                    return traversal
                if item.spec_id not in visited:
                    visit_node(self.task_dependencies[item.spec_id])

        return traversal

    @staticmethod
    def _find_root_tasks(tasks: list[ScheduledScopedTask]) -> list[ScheduledScopedTask]:
        task_ids = {task.spec_id for task in tasks}
        dep_groups: dict[tuple, list[ScheduledScopedTask]] = {}

        for task in tasks:
            key = tuple(sorted(task.specification.depends_on))
            dep_groups.setdefault(key, []).append(task)

        roots = []
        for deps, grouped in dep_groups.items():
            if all(task_id not in task_ids for task_id in deps):
                roots.extend(grouped)

        return roots

    @staticmethod
    def _find_all_parallel_groups(
        tasks: list[ScheduledScopedTask],
        filter_group: Callable[[int, int], bool],
    ) -> list[tuple[tuple[TaskSpecificationId, ...], list[ScheduledScopedTask]]]:
        deps: dict[tuple, dict] = {}

        for task in tasks:
            parents = tuple(task.specification.depends_on)
            if parents not in deps:
                deps[parents] = {"children": [task], "count": 1}
            else:
                deps[parents]["children"].append(task)
                deps[parents]["count"] += 1

        return [(parents, g["children"]) for parents, g in deps.items() if filter_group(len(parents), g["count"])]
