"""Characterization tests: Celery-canvas dispatch is behaviorally equivalent to event-driven dispatch.

The harness runs the same graph through both paths and captures:
- dispatched_spec_ids: the complete set of TaskSpecificationIds enqueued
- wave_map: spec_id → wave index (tasks dispatched together share the same wave)

Equivalence is asserted in Tasks 2 and 3. This file (Task 1) establishes the harness
and verifies that the capture utilities produce the expected output for the oracle fixtures.
"""

from dataclasses import replace
from unittest.mock import MagicMock

from src.domain.job import ScopedJob
from src.domain.scoped_task import ScheduledScopedTask, SuccessfullyFinishedScopedTask
from src.domain.task import TaskSpecificationId
from src.services.make_task_graph import LeafTask, ParallelTasks, SequentialTasks, TaskGraph
from tests.unit.domain.conftest import AT, JOB_ID, make_scheduled_task, make_spec

T = TaskSpecificationId


# ---------------------------------------------------------------------------
# Oracle fixtures (reuse same spec structure as existing domain graph tests)
# ---------------------------------------------------------------------------

def _make_linear_sequence() -> list[ScheduledScopedTask]:
    """Chain: RELOAD_PATIENT_DATA → RELOAD_MATCHED_TREATMENTS → EXPORT_TREATMENTS → PUSH_MATCHED_TREATMENTS"""
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.EXPORT_TREATMENTS, depends_on=[T.RELOAD_MATCHED_TREATMENTS])),
        make_scheduled_task(make_spec(T.PUSH_MATCHED_TREATMENTS, depends_on=[T.EXPORT_TREATMENTS])),
    ]


def _make_diamond() -> list[ScheduledScopedTask]:
    """Diamond DAG: RELOAD_PATIENT_DATA → (RELOAD_SOMATIC ∥ RELOAD_GERMLINE) → RELOAD_MATCHED_TREATMENTS"""
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.RELOAD_GERMLINE_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(
            make_spec(
                T.RELOAD_MATCHED_TREATMENTS,
                depends_on=[T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS],
            )
        ),
    ]


# ---------------------------------------------------------------------------
# Harness: canvas-path output capture
# ---------------------------------------------------------------------------

def collect_canvas_spec_ids(seq: SequentialTasks) -> set[TaskSpecificationId]:
    """Walk a SequentialTasks graph and return every spec_id present."""
    spec_ids: set[TaskSpecificationId] = set()
    for item in seq.values:
        match item:
            case LeafTask():
                spec_ids.add(item.value.spec_id)
            case ParallelTasks():
                for branch in item.value:
                    match branch:
                        case LeafTask():
                            spec_ids.add(branch.value.spec_id)
                        case SequentialTasks():
                            spec_ids |= collect_canvas_spec_ids(branch)
    return spec_ids


def canvas_wave_map(seq: SequentialTasks) -> dict[TaskSpecificationId, int]:
    """Assign a wave index to each task from the SequentialTasks chain structure.

    Sequential items get increasing wave numbers.
    Items inside a ParallelTasks (including single-element parallel groups) share the
    same starting wave; nested SequentialTasks branches each advance the wave independently,
    and the overall wave advances past the deepest branch.
    """
    wave_map: dict[TaskSpecificationId, int] = {}
    _assign_waves(seq, wave_map, start_wave=0)
    return wave_map


def _assign_waves(seq: SequentialTasks, wave_map: dict, start_wave: int) -> int:
    """Populate wave_map in-place; return the next available wave after this sequence."""
    wave = start_wave
    for item in seq.values:
        match item:
            case LeafTask():
                wave_map[item.value.spec_id] = wave
                wave += 1
            case ParallelTasks():
                max_depth = wave + 1
                for branch in item.value:
                    match branch:
                        case LeafTask():
                            wave_map[branch.value.spec_id] = wave
                        case SequentialTasks():
                            end = _assign_waves(branch, wave_map, wave)
                            max_depth = max(max_depth, end)
                wave = max_depth
    return wave


# ---------------------------------------------------------------------------
# Harness: event-driven-path output capture
# ---------------------------------------------------------------------------

def _complete_task(task: ScheduledScopedTask) -> SuccessfullyFinishedScopedTask:
    """Transition ScheduledScopedTask → SuccessfullyFinishedScopedTask for simulation."""
    return task.start(message="sim", at=AT).finish(message="sim", at=AT)


def simulate_event_driven_waves(tasks: list[ScheduledScopedTask]) -> dict[TaskSpecificationId, int]:
    """Simulate the full event-driven dispatch progression.

    Starting from an all-scheduled job, repeatedly calls dispatchable_tasks(),
    marks the current wave as finished, and collects the next wave until the
    graph is exhausted.  Returns wave_map: spec_id → wave index (0-based).
    """
    scope = MagicMock()
    scope.get_id.return_value = "sim-scope"
    job: ScopedJob = ScopedJob(id=JOB_ID, scope=scope, tasks=list(tasks))

    wave_map: dict[TaskSpecificationId, int] = {}
    wave = 0

    while True:
        dispatchable = job.dispatchable_tasks()
        if not dispatchable:
            break
        for t in dispatchable:
            wave_map[t.spec_id] = wave
        finished = {t.spec_id: _complete_task(t) for t in dispatchable}
        new_tasks = [finished.get(t.spec_id, t) for t in job.tasks]
        job = replace(job, tasks=new_tasks)
        wave += 1

    return wave_map


# ---------------------------------------------------------------------------
# Helper: extract direct dependency edges from task specs
# ---------------------------------------------------------------------------

def direct_dependency_edges(
    tasks: list[ScheduledScopedTask],
) -> set[tuple[TaskSpecificationId, TaskSpecificationId]]:
    """Return {(pred, succ)} for every explicit depends_on relationship."""
    return {
        (pred_id, task.spec_id)
        for task in tasks
        for pred_id in task.specification.depends_on
    }


# ---------------------------------------------------------------------------
# Tests: fixture loading
# ---------------------------------------------------------------------------

class TestFixtureLoading:
    def test_linear_fixture_produces_four_scheduled_tasks(self):
        tasks = _make_linear_sequence()
        assert len(tasks) == 4
        assert all(isinstance(t, ScheduledScopedTask) for t in tasks)

    def test_linear_fixture_spec_ids(self):
        tasks = _make_linear_sequence()
        ids = [t.spec_id for t in tasks]
        assert T.RELOAD_PATIENT_DATA in ids
        assert T.RELOAD_MATCHED_TREATMENTS in ids
        assert T.EXPORT_TREATMENTS in ids
        assert T.PUSH_MATCHED_TREATMENTS in ids

    def test_diamond_fixture_produces_four_scheduled_tasks(self):
        tasks = _make_diamond()
        assert len(tasks) == 4
        assert all(isinstance(t, ScheduledScopedTask) for t in tasks)

    def test_diamond_fixture_spec_ids(self):
        tasks = _make_diamond()
        ids = [t.spec_id for t in tasks]
        assert T.RELOAD_PATIENT_DATA in ids
        assert T.RELOAD_SOMATIC_MUTATIONS in ids
        assert T.RELOAD_GERMLINE_MUTATIONS in ids
        assert T.RELOAD_MATCHED_TREATMENTS in ids

    def test_single_task_fixture(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        assert len(tasks) == 1
        assert isinstance(tasks[0], ScheduledScopedTask)


# ---------------------------------------------------------------------------
# Tests: canvas output capture
# ---------------------------------------------------------------------------

class TestCanvasOutputCapture:
    def test_collect_spec_ids_linear(self):
        tasks = _make_linear_sequence()
        graph = TaskGraph(tasks).make_graph()
        spec_ids = collect_canvas_spec_ids(graph)
        assert spec_ids == {
            T.RELOAD_PATIENT_DATA,
            T.RELOAD_MATCHED_TREATMENTS,
            T.EXPORT_TREATMENTS,
            T.PUSH_MATCHED_TREATMENTS,
        }

    def test_collect_spec_ids_diamond(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        spec_ids = collect_canvas_spec_ids(graph)
        assert spec_ids == {
            T.RELOAD_PATIENT_DATA,
            T.RELOAD_SOMATIC_MUTATIONS,
            T.RELOAD_GERMLINE_MUTATIONS,
            T.RELOAD_MATCHED_TREATMENTS,
        }

    def test_collect_spec_ids_single_task(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        graph = TaskGraph(tasks).make_graph()
        spec_ids = collect_canvas_spec_ids(graph)
        assert spec_ids == {T.RELOAD_PATIENT_DATA}

    def test_canvas_wave_map_linear_strictly_ordered(self):
        tasks = _make_linear_sequence()
        graph = TaskGraph(tasks).make_graph()
        waves = canvas_wave_map(graph)
        assert waves[T.RELOAD_PATIENT_DATA] < waves[T.RELOAD_MATCHED_TREATMENTS]
        assert waves[T.RELOAD_MATCHED_TREATMENTS] < waves[T.EXPORT_TREATMENTS]
        assert waves[T.EXPORT_TREATMENTS] < waves[T.PUSH_MATCHED_TREATMENTS]

    def test_canvas_wave_map_diamond_parallel_same_wave(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        waves = canvas_wave_map(graph)
        assert waves[T.RELOAD_SOMATIC_MUTATIONS] == waves[T.RELOAD_GERMLINE_MUTATIONS]

    def test_canvas_wave_map_diamond_root_before_parallel(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        waves = canvas_wave_map(graph)
        assert waves[T.RELOAD_PATIENT_DATA] < waves[T.RELOAD_SOMATIC_MUTATIONS]
        assert waves[T.RELOAD_PATIENT_DATA] < waves[T.RELOAD_GERMLINE_MUTATIONS]

    def test_canvas_wave_map_diamond_parallel_before_fan_in(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        waves = canvas_wave_map(graph)
        assert waves[T.RELOAD_SOMATIC_MUTATIONS] < waves[T.RELOAD_MATCHED_TREATMENTS]
        assert waves[T.RELOAD_GERMLINE_MUTATIONS] < waves[T.RELOAD_MATCHED_TREATMENTS]

    def test_canvas_wave_map_single_task_is_wave_zero(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        graph = TaskGraph(tasks).make_graph()
        waves = canvas_wave_map(graph)
        assert waves[T.RELOAD_PATIENT_DATA] == 0


# ---------------------------------------------------------------------------
# Tests: event-driven output capture
# ---------------------------------------------------------------------------

class TestEventDrivenOutputCapture:
    def test_simulation_linear_covers_all_tasks(self):
        tasks = _make_linear_sequence()
        waves = simulate_event_driven_waves(tasks)
        assert set(waves.keys()) == {
            T.RELOAD_PATIENT_DATA,
            T.RELOAD_MATCHED_TREATMENTS,
            T.EXPORT_TREATMENTS,
            T.PUSH_MATCHED_TREATMENTS,
        }

    def test_simulation_diamond_covers_all_tasks(self):
        tasks = _make_diamond()
        waves = simulate_event_driven_waves(tasks)
        assert set(waves.keys()) == {
            T.RELOAD_PATIENT_DATA,
            T.RELOAD_SOMATIC_MUTATIONS,
            T.RELOAD_GERMLINE_MUTATIONS,
            T.RELOAD_MATCHED_TREATMENTS,
        }

    def test_simulation_single_task_wave_zero(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        waves = simulate_event_driven_waves(tasks)
        assert waves == {T.RELOAD_PATIENT_DATA: 0}

    def test_simulation_linear_root_dispatched_first(self):
        tasks = _make_linear_sequence()
        waves = simulate_event_driven_waves(tasks)
        assert waves[T.RELOAD_PATIENT_DATA] == 0

    def test_simulation_diamond_parallel_pair_at_same_wave(self):
        tasks = _make_diamond()
        waves = simulate_event_driven_waves(tasks)
        assert waves[T.RELOAD_SOMATIC_MUTATIONS] == waves[T.RELOAD_GERMLINE_MUTATIONS]

    def test_simulation_diamond_fan_in_dispatched_after_parallel(self):
        tasks = _make_diamond()
        waves = simulate_event_driven_waves(tasks)
        assert waves[T.RELOAD_SOMATIC_MUTATIONS] < waves[T.RELOAD_MATCHED_TREATMENTS]
        assert waves[T.RELOAD_GERMLINE_MUTATIONS] < waves[T.RELOAD_MATCHED_TREATMENTS]


# ---------------------------------------------------------------------------
# Fixtures: additional linear sequences for edge-case coverage
# ---------------------------------------------------------------------------

def _make_two_node_chain() -> list[ScheduledScopedTask]:
    """Chain of length 2: RELOAD_PATIENT_DATA → RELOAD_MATCHED_TREATMENTS"""
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA])),
    ]


# ---------------------------------------------------------------------------
# Tests: linear equivalence assertions (Task 2)
# ---------------------------------------------------------------------------

class TestLinearEquivalence:
    """Both dispatch paths produce the same observable behavior for linear graphs."""

    # -- task-set equivalence -------------------------------------------------

    def test_four_node_chain_task_sets_match(self):
        tasks = _make_linear_sequence()
        graph = TaskGraph(tasks).make_graph()
        canvas_ids = collect_canvas_spec_ids(graph)
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert canvas_ids == event_ids

    def test_single_node_task_sets_match(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        graph = TaskGraph(tasks).make_graph()
        canvas_ids = collect_canvas_spec_ids(graph)
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert canvas_ids == event_ids

    def test_two_node_chain_task_sets_match(self):
        tasks = _make_two_node_chain()
        graph = TaskGraph(tasks).make_graph()
        canvas_ids = collect_canvas_spec_ids(graph)
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert canvas_ids == event_ids

    # -- happens-before equivalence -------------------------------------------

    def test_four_node_chain_happens_before_preserved(self):
        tasks = _make_linear_sequence()
        event_waves = simulate_event_driven_waves(tasks)
        for pred_id, succ_id in direct_dependency_edges(tasks):
            assert event_waves[pred_id] < event_waves[succ_id], (
                f"event-driven violated dependency {pred_id} → {succ_id}: "
                f"wave {event_waves[pred_id]} not < {event_waves[succ_id]}"
            )

    def test_two_node_chain_happens_before_preserved(self):
        tasks = _make_two_node_chain()
        event_waves = simulate_event_driven_waves(tasks)
        assert event_waves[T.RELOAD_PATIENT_DATA] < event_waves[T.RELOAD_MATCHED_TREATMENTS]

    def test_single_node_no_dependency_edges(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        assert direct_dependency_edges(tasks) == set()

    # -- ordering equivalence (canvas order == event-driven order) ------------

    def test_four_node_chain_relative_order_equivalent(self):
        """For every pair of tasks, canvas and event-driven agree on which comes first."""
        tasks = _make_linear_sequence()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        spec_ids = list(canvas_waves.keys())
        for i, a in enumerate(spec_ids):
            for b in spec_ids[i + 1:]:
                canvas_before = canvas_waves[a] < canvas_waves[b]
                event_before = event_waves[a] < event_waves[b]
                assert canvas_before == event_before, (
                    f"ordering disagreement for {a} vs {b}: "
                    f"canvas_before={canvas_before}, event_before={event_before}"
                )

    def test_two_node_chain_relative_order_equivalent(self):
        tasks = _make_two_node_chain()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        assert (canvas_waves[T.RELOAD_PATIENT_DATA] < canvas_waves[T.RELOAD_MATCHED_TREATMENTS]) == (
            event_waves[T.RELOAD_PATIENT_DATA] < event_waves[T.RELOAD_MATCHED_TREATMENTS]
        )

    def test_single_node_equivalence(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        assert set(canvas_waves.keys()) == set(event_waves.keys())
        assert canvas_waves[T.RELOAD_PATIENT_DATA] == 0
        assert event_waves[T.RELOAD_PATIENT_DATA] == 0


# ---------------------------------------------------------------------------
# Fixtures: parallel graph shapes for Task 3
# ---------------------------------------------------------------------------

def _make_sibling_parallel() -> list[ScheduledScopedTask]:
    """Fan-out (no fan-in): RELOAD_PATIENT_DATA → (RELOAD_SOMATIC ∥ RELOAD_GERMLINE ∥ RELOAD_HLA_ALLELES)"""
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.RELOAD_GERMLINE_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.RELOAD_HLA_ALLELES, depends_on=[T.RELOAD_PATIENT_DATA])),
    ]


# ---------------------------------------------------------------------------
# Tests: parallel equivalence assertions (Task 3)
# ---------------------------------------------------------------------------

class TestParallelEquivalence:
    """Both dispatch paths produce the same observable behavior for parallel graphs."""

    # -- task-set equivalence -------------------------------------------------

    def test_diamond_task_sets_match(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        canvas_ids = collect_canvas_spec_ids(graph)
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert canvas_ids == event_ids

    def test_sibling_parallel_task_sets_match(self):
        tasks = _make_sibling_parallel()
        graph = TaskGraph(tasks).make_graph()
        canvas_ids = collect_canvas_spec_ids(graph)
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert canvas_ids == event_ids

    # -- happens-before equivalence -------------------------------------------

    def test_diamond_happens_before_preserved(self):
        tasks = _make_diamond()
        event_waves = simulate_event_driven_waves(tasks)
        for pred_id, succ_id in direct_dependency_edges(tasks):
            assert event_waves[pred_id] < event_waves[succ_id], (
                f"event-driven violated dependency {pred_id} → {succ_id}: "
                f"wave {event_waves[pred_id]} not < {event_waves[succ_id]}"
            )

    def test_sibling_parallel_happens_before_preserved(self):
        tasks = _make_sibling_parallel()
        event_waves = simulate_event_driven_waves(tasks)
        for pred_id, succ_id in direct_dependency_edges(tasks):
            assert event_waves[pred_id] < event_waves[succ_id], (
                f"event-driven violated dependency {pred_id} → {succ_id}: "
                f"wave {event_waves[pred_id]} not < {event_waves[succ_id]}"
            )

    # -- fan-out ordering equivalence -----------------------------------------

    def test_diamond_fan_out_root_before_parallel_in_both_paths(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        for sibling in (T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS):
            assert canvas_waves[T.RELOAD_PATIENT_DATA] < canvas_waves[sibling]
            assert event_waves[T.RELOAD_PATIENT_DATA] < event_waves[sibling]

    def test_sibling_parallel_root_before_all_children_in_both_paths(self):
        tasks = _make_sibling_parallel()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        for child in (T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS, T.RELOAD_HLA_ALLELES):
            assert canvas_waves[T.RELOAD_PATIENT_DATA] < canvas_waves[child]
            assert event_waves[T.RELOAD_PATIENT_DATA] < event_waves[child]

    # -- fan-in ordering equivalence ------------------------------------------

    def test_diamond_fan_in_parallel_before_convergence_in_both_paths(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        for sibling in (T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS):
            assert canvas_waves[sibling] < canvas_waves[T.RELOAD_MATCHED_TREATMENTS]
            assert event_waves[sibling] < event_waves[T.RELOAD_MATCHED_TREATMENTS]

    # -- sibling co-dispatch equivalence --------------------------------------

    def test_diamond_siblings_dispatched_same_wave_in_both_paths(self):
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        assert canvas_waves[T.RELOAD_SOMATIC_MUTATIONS] == canvas_waves[T.RELOAD_GERMLINE_MUTATIONS]
        assert event_waves[T.RELOAD_SOMATIC_MUTATIONS] == event_waves[T.RELOAD_GERMLINE_MUTATIONS]

    def test_sibling_parallel_all_children_same_wave_in_both_paths(self):
        tasks = _make_sibling_parallel()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        children = [T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS, T.RELOAD_HLA_ALLELES]
        canvas_child_waves = {canvas_waves[c] for c in children}
        event_child_waves = {event_waves[c] for c in children}
        assert len(canvas_child_waves) == 1, "canvas: all siblings must share a wave"
        assert len(event_child_waves) == 1, "event-driven: all siblings must share a wave"

    # -- full relative ordering equivalence -----------------------------------

    def test_diamond_relative_order_equivalent(self):
        """For every task pair, canvas and event-driven agree on strict-before / same-wave."""
        tasks = _make_diamond()
        graph = TaskGraph(tasks).make_graph()
        canvas_waves = canvas_wave_map(graph)
        event_waves = simulate_event_driven_waves(tasks)
        spec_ids = list(canvas_waves.keys())
        for i, a in enumerate(spec_ids):
            for b in spec_ids[i + 1:]:
                canvas_a_lt_b = canvas_waves[a] < canvas_waves[b]
                canvas_b_lt_a = canvas_waves[b] < canvas_waves[a]
                event_a_lt_b = event_waves[a] < event_waves[b]
                event_b_lt_a = event_waves[b] < event_waves[a]
                assert canvas_a_lt_b == event_a_lt_b, (
                    f"ordering disagreement {a} < {b}: canvas={canvas_a_lt_b}, event={event_a_lt_b}"
                )
                assert canvas_b_lt_a == event_b_lt_a, (
                    f"ordering disagreement {b} < {a}: canvas={canvas_b_lt_a}, event={event_b_lt_a}"
                )
