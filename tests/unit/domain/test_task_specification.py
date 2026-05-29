from src.domain.task import TaskSpecification, TaskSpecificationId


def test_match_returns_true_for_same_id():
    spec = TaskSpecification(id=TaskSpecificationId.RELOAD_PATIENT_DATA, label="reload", description="", depends_on=[])
    assert spec.match(TaskSpecificationId.RELOAD_PATIENT_DATA) is True


def test_match_returns_false_for_different_id():
    spec = TaskSpecification(id=TaskSpecificationId.RELOAD_PATIENT_DATA, label="reload", description="", depends_on=[])
    assert spec.match(TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS) is False


def test_is_dependent_true():
    spec = TaskSpecification(
        id=TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS,
        label="somatic",
        description="",
        depends_on=[TaskSpecificationId.RELOAD_PATIENT_DATA],
    )
    assert spec.is_dependent(TaskSpecificationId.RELOAD_PATIENT_DATA) is True


def test_is_dependent_false():
    spec = TaskSpecification(
        id=TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS,
        label="somatic",
        description="",
        depends_on=[TaskSpecificationId.RELOAD_PATIENT_DATA],
    )
    assert spec.is_dependent(TaskSpecificationId.RELOAD_GERMLINE_MUTATIONS) is False


def test_merge_updates_label_description_depends_on():
    original = TaskSpecification(
        id=TaskSpecificationId.RELOAD_PATIENT_DATA, label="old", description="old desc", depends_on=[]
    )
    updated = TaskSpecification(
        id=TaskSpecificationId.RELOAD_PATIENT_DATA,
        label="new",
        description="new desc",
        depends_on=[TaskSpecificationId.SET_REPORT_VERSION],
    )
    merged = original.merge(updated)
    assert merged.id == TaskSpecificationId.RELOAD_PATIENT_DATA
    assert merged.label == "new"
    assert merged.description == "new desc"
    assert merged.depends_on == [TaskSpecificationId.SET_REPORT_VERSION]


def test_task_specification_id_order():
    assert TaskSpecificationId.RELOAD_PATIENT_DATA.order < TaskSpecificationId.RELOAD_MATCHED_TREATMENTS.order
    assert TaskSpecificationId.RELOAD_MATCHED_TREATMENTS.order < TaskSpecificationId.EXPORT_TREATMENTS.order
    assert TaskSpecificationId.EXPORT_TREATMENTS.order < TaskSpecificationId.PUSH_MATCHED_TREATMENTS.order
