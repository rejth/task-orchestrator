import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from task_orchestrator.domain.task import TaskSpecificationId
from task_orchestrator.services.task_dispatcher import TaskDispatcher
from tests.unit.domain.conftest import make_scheduled_task, make_spec

SCOPE_ID = "patient-123"
USER = "user@example.com"


@pytest.fixture
def dispatcher():
    return TaskDispatcher(broker=MagicMock(), expiry_seconds=3600)


def test_each_task_enqueued_independently(dispatcher):
    """Each task in a batch gets its own Celery Signature and apply_async call."""
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_PATIENT_PARAMETERS)
    tasks = [make_scheduled_task(spec_a), make_scheduled_task(spec_b)]

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        instances = [MagicMock(), MagicMock()]
        MockSig.side_effect = instances

        dispatcher.dispatch(tasks, scope_id=SCOPE_ID, user=USER)

    assert instances[0].apply_async.call_count == 1
    assert instances[1].apply_async.call_count == 1


def test_launch_id_is_celery_task_id(dispatcher):
    """The launch UUID is passed as Celery task_id for idempotent enqueue."""
    launch_id = uuid4()
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec, launch_id=launch_id)

    captured_kwargs: list[dict] = []

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_kwargs.append(kw), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert captured_kwargs[0]["options"]["task_id"] == str(launch_id)


def test_signatures_are_immutable(dispatcher):
    """Dispatched Celery signatures are marked immutable."""
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)

    captured_kwargs: list[dict] = []

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_kwargs.append(kw), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert captured_kwargs[0]["immutable"] is True


def test_each_signature_has_no_broker_level_expiry(dispatcher):
    """Dispatched signatures do not set broker-level expires."""
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)

    captured_kwargs: list[dict] = []

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_kwargs.append(kw), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert "expires" not in captured_kwargs[0]


def test_signature_args_match_task(dispatcher):
    """Signature args include scope_id, spec_id, launch_id, and user."""
    launch_id = uuid4()
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec, launch_id=launch_id)

    captured_args: list[tuple] = []

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_args.append(kw.get("args", ())), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    # First 4 args are fixed; 5th is expires_at ISO string (tested separately)
    assert captured_args[0][:4] == (SCOPE_ID, spec.id.value, str(launch_id), USER)


def test_empty_task_list_enqueues_nothing(dispatcher):
    """Dispatching an empty task list creates no signatures."""
    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        dispatcher.dispatch([], scope_id=SCOPE_ID, user=USER)

    MockSig.assert_not_called()


def test_duplicate_dispatch_uses_same_task_id(dispatcher):
    """Both dispatches use the same launch_id as task_id — idempotency key is stable."""
    launch_id = uuid4()
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec, launch_id=launch_id)

    captured_task_ids: list[str] = []

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_task_ids.append(kw["options"]["task_id"]), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)
        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert len(captured_task_ids) == 2
    assert captured_task_ids[0] == captured_task_ids[1] == str(launch_id)


def test_enqueued_set_matches_dispatched_tasks(dispatcher):
    """Every dispatched task appears in the enqueued set exactly once."""
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_PATIENT_PARAMETERS)
    launch_id_a = uuid4()
    launch_id_b = uuid4()
    task_a = make_scheduled_task(spec_a, launch_id=launch_id_a)
    task_b = make_scheduled_task(spec_b, launch_id=launch_id_b)

    enqueued_task_ids: set[str] = set()

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (enqueued_task_ids.add(kw["options"]["task_id"]), MagicMock())[1]

        dispatcher.dispatch([task_a, task_b], scope_id=SCOPE_ID, user=USER)

    assert enqueued_task_ids == {str(launch_id_a), str(launch_id_b)}


def test_dispatcher_includes_expires_at_in_args(dispatcher):
    """Task args include expires_at ISO string so task_runner can detect expiry at processing time."""
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)

    captured_args: list[tuple] = []
    before = datetime.datetime.now(datetime.timezone.utc)

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_args.append(kw.get("args", ())), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    args = captured_args[0]
    assert len(args) == 5
    expires_at_str = args[4]
    expires_at_dt = datetime.datetime.fromisoformat(expires_at_str)
    assert expires_at_dt > before
    assert expires_at_dt <= before + datetime.timedelta(seconds=3601)


@pytest.mark.parametrize("bad_expiry", [0, -1, -100])
def test_zero_or_negative_expiry_raises(bad_expiry):
    """TaskDispatcher rejects zero or negative expiry_seconds."""
    with pytest.raises(ValueError, match="expiry_seconds must be positive"):
        TaskDispatcher(broker=MagicMock(), expiry_seconds=bad_expiry)


def test_all_tasks_in_batch_share_same_expiry_reference(dispatcher):
    """All tasks in one dispatch call use the same now reference — no per-task drift."""
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_PATIENT_PARAMETERS)
    tasks = [make_scheduled_task(spec_a), make_scheduled_task(spec_b)]

    captured_expiries: list[str] = []

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_expiries.append(kw["args"][4]), MagicMock())[1]

        dispatcher.dispatch(tasks, scope_id=SCOPE_ID, user=USER)

    assert len(captured_expiries) == 2
    assert captured_expiries[0] == captured_expiries[1]
