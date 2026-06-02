"""Linear (no-parallel) task graph tests.

Chain: RELOAD_PATIENT_DATA → RELOAD_MATCHED_TREATMENTS → EXPORT_TREATMENTS → PUSH_MATCHED_TREATMENTS
"""

from src.domain.task import TaskSpecificationId
from src.services.make_task_graph import LeafTask, SequentialTasks, TaskGraph
from tests.unit.domain.conftest import make_scheduled_task, make_spec

T = TaskSpecificationId


def _make_linear_sequence() -> list:
    return [
        make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA)),
        make_scheduled_task(make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA])),
        make_scheduled_task(make_spec(T.EXPORT_TREATMENTS, depends_on=[T.RELOAD_MATCHED_TREATMENTS])),
        make_scheduled_task(make_spec(T.PUSH_MATCHED_TREATMENTS, depends_on=[T.EXPORT_TREATMENTS])),
    ]


def test_linear_graph_is_sequential():
    result = TaskGraph(_make_linear_sequence()).make_graph()
    assert isinstance(result, SequentialTasks)


def test_linear_graph_all_leaf_tasks():
    result = TaskGraph(_make_linear_sequence()).make_graph()
    for item in result.values:
        assert isinstance(item, LeafTask)


def test_linear_graph_sorted_correctly():
    graph = TaskGraph(_make_linear_sequence())
    graph.make_graph()
    ids = [t.spec_id for t in graph.sorted_tasks]
    assert ids.index(T.RELOAD_PATIENT_DATA) < ids.index(T.RELOAD_MATCHED_TREATMENTS)
    assert ids.index(T.RELOAD_MATCHED_TREATMENTS) < ids.index(T.EXPORT_TREATMENTS)
    assert ids.index(T.EXPORT_TREATMENTS) < ids.index(T.PUSH_MATCHED_TREATMENTS)


def test_single_task_graph():
    result = TaskGraph([make_scheduled_task(make_spec(T.RELOAD_PATIENT_DATA))]).make_graph()
    assert isinstance(result, SequentialTasks)
    assert len(result.values) == 1
    assert isinstance(result.values[0], LeafTask)
