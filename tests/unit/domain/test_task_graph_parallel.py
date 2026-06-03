"""Parallel branch task graph tests.

Diamond DAG:
    RELOAD_PATIENT_DATA
        ├──▶ RELOAD_SOMATIC_MUTATIONS  ─┐
        └──▶ RELOAD_GERMLINE_MUTATIONS ──▶ RELOAD_MATCHED_TREATMENTS
"""

from src.domain.task import TaskSpecificationId
from src.services.make_task_graph import LeafTask, ParallelTasks, TaskGraph
from tests.unit.domain.conftest import make_scheduled_task, make_spec

T = TaskSpecificationId


def _make_diamond() -> list:
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


def test_diamond_graph_has_parallel_group():
    result = TaskGraph(_make_diamond()).make_graph()
    assert any(isinstance(v, ParallelTasks) for v in result.values)


def test_diamond_graph_patient_data_is_first_leaf():
    result = TaskGraph(_make_diamond()).make_graph()
    first = result.values[0]
    assert isinstance(first, LeafTask)
    assert first.value.spec_id == T.RELOAD_PATIENT_DATA


def test_diamond_graph_parallel_contains_somatic_and_germline():
    result = TaskGraph(_make_diamond()).make_graph()
    parallel = next(v for v in result.values if isinstance(v, ParallelTasks))
    leaf_ids = {item.value.spec_id for item in parallel.value if isinstance(item, LeafTask)}
    assert T.RELOAD_SOMATIC_MUTATIONS in leaf_ids
    assert T.RELOAD_GERMLINE_MUTATIONS in leaf_ids


def test_diamond_sorted_topologically():
    graph = TaskGraph(_make_diamond())
    graph.make_graph()
    ids = [t.spec_id for t in graph.sorted_tasks]
    assert ids.index(T.RELOAD_PATIENT_DATA) < ids.index(T.RELOAD_SOMATIC_MUTATIONS)
    assert ids.index(T.RELOAD_PATIENT_DATA) < ids.index(T.RELOAD_GERMLINE_MUTATIONS)
    assert ids.index(T.RELOAD_SOMATIC_MUTATIONS) < ids.index(T.RELOAD_MATCHED_TREATMENTS)
    assert ids.index(T.RELOAD_GERMLINE_MUTATIONS) < ids.index(T.RELOAD_MATCHED_TREATMENTS)
