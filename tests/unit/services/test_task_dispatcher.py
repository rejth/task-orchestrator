from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.task import TaskSpecificationId
from src.services.task_dispatcher import TaskDispatcher
from tests.unit.domain.conftest import make_scheduled_task, make_spec

SCOPE_ID = "patient-123"
USER = "user@example.com"


@pytest.fixture
def dispatcher():
    return TaskDispatcher(broker=MagicMock(), expiry_seconds=3600)


def test_each_task_enqueued_independently(dispatcher):
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_PATIENT_PARAMETERS)
    tasks = [make_scheduled_task(spec_a), make_scheduled_task(spec_b)]

    with patch("src.services.task_dispatcher.Signature") as MockSig:
        instances = [MagicMock(), MagicMock()]
        MockSig.side_effect = instances

        dispatcher.dispatch(tasks, scope_id=SCOPE_ID, user=USER)

    assert instances[0].apply_async.call_count == 1
    assert instances[1].apply_async.call_count == 1


def test_launch_id_is_celery_task_id(dispatcher):
    launch_id = uuid4()
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec, launch_id=launch_id)

    captured_kwargs: list[dict] = []

    with patch("src.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_kwargs.append(kw), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert captured_kwargs[0]["options"]["task_id"] == str(launch_id)


def test_signatures_are_immutable(dispatcher):
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)

    captured_kwargs: list[dict] = []

    with patch("src.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_kwargs.append(kw), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert captured_kwargs[0]["immutable"] is True


def test_each_signature_has_expiry(dispatcher):
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)

    captured_kwargs: list[dict] = []

    with patch("src.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (captured_kwargs.append(kw), MagicMock())[1]

        dispatcher.dispatch([task], scope_id=SCOPE_ID, user=USER)

    assert captured_kwargs[0]["expires"] is not None


def test_empty_task_list_enqueues_nothing(dispatcher):
    with patch("src.services.task_dispatcher.Signature") as MockSig:
        dispatcher.dispatch([], scope_id=SCOPE_ID, user=USER)

    MockSig.assert_not_called()
