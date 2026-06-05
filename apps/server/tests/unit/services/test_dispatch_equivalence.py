"""Characterization tests: event-driven dispatch produces correct ordering behavior.

The harness simulates the full event-driven dispatch progression and captures:
- dispatched_spec_ids: the complete set of TaskSpecificationIds enqueued
- wave_map: spec_id → wave index (tasks dispatched together share the same wave)
"""

from dataclasses import replace
from unittest.mock import MagicMock

from task_orchestrator.domain.job import ScopedJob
from task_orchestrator.domain.scoped_task import ScheduledScopedTask, SuccessfullyFinishedScopedTask
from task_orchestrator.domain.task import TaskSpecificationId
from tests.unit.domain.conftest import AT, JOB_ID, make_scheduled_task, make_spec

T = TaskSpecificationId


# ---------------------------------------------------------------------------
# Oracle fixtures
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


def _make_two_node_chain() -> list[ScheduledScopedTask]:
    """Chain of length 2: RELOAD_PATIENT_DATA → RELOAD_MATCHED_TREATMENTS"""
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA])),
    ]


def _make_sibling_parallel() -> list[ScheduledScopedTask]:
    """Fan-out (no fan-in): RELOAD_PATIENT_DATA → (RELOAD_SOMATIC ∥ RELOAD_GERMLINE ∥ RELOAD_HLA_ALLELES)"""
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.RELOAD_GERMLINE_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.RELOAD_HLA_ALLELES, depends_on=[T.RELOAD_PATIENT_DATA])),
    ]


# ---------------------------------------------------------------------------
# Harness: event-driven-path output capture
# ---------------------------------------------------------------------------


def _complete_task(task: ScheduledScopedTask) -> SuccessfullyFinishedScopedTask:
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
    return {(pred_id, task.spec_id) for task in tasks for pred_id in task.specification.depends_on}


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
# Tests: linear ordering
# ---------------------------------------------------------------------------


class TestLinearOrdering:
    """Event-driven dispatch produces correct ordering for linear graphs."""

    def test_single_node_covers_task(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert event_ids == {T.RELOAD_PATIENT_DATA}

    def test_two_node_chain_covers_both_tasks(self):
        tasks = _make_two_node_chain()
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert event_ids == {T.RELOAD_PATIENT_DATA, T.RELOAD_MATCHED_TREATMENTS}

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

    def test_four_node_chain_strictly_ordered(self):
        tasks = _make_linear_sequence()
        event_waves = simulate_event_driven_waves(tasks)
        assert event_waves[T.RELOAD_PATIENT_DATA] < event_waves[T.RELOAD_MATCHED_TREATMENTS]
        assert event_waves[T.RELOAD_MATCHED_TREATMENTS] < event_waves[T.EXPORT_TREATMENTS]
        assert event_waves[T.EXPORT_TREATMENTS] < event_waves[T.PUSH_MATCHED_TREATMENTS]

    def test_single_node_at_wave_zero(self):
        tasks = [make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]
        event_waves = simulate_event_driven_waves(tasks)
        assert event_waves[T.RELOAD_PATIENT_DATA] == 0


# ---------------------------------------------------------------------------
# Tests: parallel ordering
# ---------------------------------------------------------------------------


class TestParallelOrdering:
    """Event-driven dispatch produces correct ordering for parallel graphs."""

    def test_diamond_covers_all_tasks(self):
        tasks = _make_diamond()
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert event_ids == {
            T.RELOAD_PATIENT_DATA,
            T.RELOAD_SOMATIC_MUTATIONS,
            T.RELOAD_GERMLINE_MUTATIONS,
            T.RELOAD_MATCHED_TREATMENTS,
        }

    def test_sibling_parallel_covers_all_tasks(self):
        tasks = _make_sibling_parallel()
        event_ids = set(simulate_event_driven_waves(tasks).keys())
        assert event_ids == {
            T.RELOAD_PATIENT_DATA,
            T.RELOAD_SOMATIC_MUTATIONS,
            T.RELOAD_GERMLINE_MUTATIONS,
            T.RELOAD_HLA_ALLELES,
        }

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

    def test_diamond_fan_out_root_before_parallel(self):
        tasks = _make_diamond()
        event_waves = simulate_event_driven_waves(tasks)
        for sibling in (T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS):
            assert event_waves[T.RELOAD_PATIENT_DATA] < event_waves[sibling]

    def test_sibling_parallel_root_before_all_children(self):
        tasks = _make_sibling_parallel()
        event_waves = simulate_event_driven_waves(tasks)
        for child in (T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS, T.RELOAD_HLA_ALLELES):
            assert event_waves[T.RELOAD_PATIENT_DATA] < event_waves[child]

    def test_diamond_fan_in_parallel_before_convergence(self):
        tasks = _make_diamond()
        event_waves = simulate_event_driven_waves(tasks)
        for sibling in (T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS):
            assert event_waves[sibling] < event_waves[T.RELOAD_MATCHED_TREATMENTS]

    def test_diamond_siblings_dispatched_same_wave(self):
        tasks = _make_diamond()
        event_waves = simulate_event_driven_waves(tasks)
        assert event_waves[T.RELOAD_SOMATIC_MUTATIONS] == event_waves[T.RELOAD_GERMLINE_MUTATIONS]

    def test_sibling_parallel_all_children_same_wave(self):
        tasks = _make_sibling_parallel()
        event_waves = simulate_event_driven_waves(tasks)
        children = [T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_GERMLINE_MUTATIONS, T.RELOAD_HLA_ALLELES]
        event_child_waves = {event_waves[c] for c in children}
        assert len(event_child_waves) == 1, "event-driven: all siblings must share a wave"

    def test_diamond_relative_order_correct(self):
        """For every task pair, event-driven respects dependency ordering."""
        tasks = _make_diamond()
        event_waves = simulate_event_driven_waves(tasks)
        for pred_id, succ_id in direct_dependency_edges(tasks):
            assert event_waves[pred_id] < event_waves[succ_id]
