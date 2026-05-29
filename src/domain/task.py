from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto


class TaskSpecificationId(str, Enum):
    # ── data loading ──────────────────────────────────────────────────────────
    RELOAD_PATIENT_DATA = ("RELOAD_PATIENT_DATA", auto())
    RELOAD_PATIENT_PARAMETERS = ("RELOAD_PATIENT_PARAMETERS", auto())
    RELOAD_HLA_ALLELES = ("RELOAD_HLA_ALLELES", auto())
    RELOAD_SEGMENT_COPY_NUMBER_ALTERATIONS = ("RELOAD_SEGMENT_COPY_NUMBER_ALTERATIONS", auto())
    RELOAD_EXON_COPY_NUMBER_ALTERATIONS = ("RELOAD_EXON_COPY_NUMBER_ALTERATIONS", auto())
    RELOAD_LOH_COPY_NUMBER_ALTERATIONS = ("RELOAD_LOH_COPY_NUMBER_ALTERATIONS", auto())
    RELOAD_MALIGNANT_CELL_CLONES = ("RELOAD_MALIGNANT_CELL_CLONES", auto())
    RELOAD_MATCHED_TREATMENTS = ("RELOAD_MATCHED_TREATMENTS", auto())
    RELOAD_COMPLEX_MEASURES = ("RELOAD_COMPLEX_MEASURES", auto())
    RELOAD_SOMATIC_MUTATIONS = ("RELOAD_SOMATIC_MUTATIONS", auto())
    RELOAD_GERMLINE_MUTATIONS = ("RELOAD_GERMLINE_MUTATIONS", auto())
    RELOAD_FUSIONS = ("RELOAD_FUSIONS", auto())
    RELOAD_CELL_POPULATIONS = ("RELOAD_CELL_POPULATIONS", auto())
    RELOAD_COPY_NUMBER_ALTERATIONS = ("RELOAD_COPY_NUMBER_ALTERATIONS", auto())
    RELOAD_GENE_EXPRESSIONS = ("RELOAD_GENE_EXPRESSIONS", auto())
    RELOAD_REARRANGEMENTS = ("RELOAD_REARRANGEMENTS", auto())
    RELOAD_GENESETS = ("RELOAD_GENESETS", auto())
    RELOAD_ORDER_SUMMARY = ("RELOAD_ORDER_SUMMARY", auto())
    RELOAD_SIGNALING_BIOMARKERS = ("RELOAD_SIGNALING_BIOMARKERS", auto())
    RELOAD_ASTRAEA_PREDICTIVE_BIOMARKERS = ("RELOAD_ASTRAEA_PREDICTIVE_BIOMARKERS", auto())
    RELOAD_MATCHED_CONTRAINDICATIONS = ("RELOAD_MATCHED_CONTRAINDICATIONS", auto())
    RELOAD_BIOLOGICAL_PROCESSES = ("RELOAD_BIOLOGICAL_PROCESSES", auto())
    RELOAD_REPORT_PARAMETERS = ("RELOAD_REPORT_PARAMETERS", auto())
    RELOAD_INVESTIGATIONAL_CLINICAL_EVIDENCE = ("RELOAD_INVESTIGATIONAL_CLINICAL_EVIDENCE", auto())
    RELOAD_NCCN_CLINICAL_EVIDENCE = ("RELOAD_NCCN_CLINICAL_EVIDENCE", auto())
    # ── setup ─────────────────────────────────────────────────────────────────
    CREATE_TREATMENT_SETTINGS = ("CREATE_TREATMENT_SETTINGS", auto())
    SET_REPORT_VERSION = ("SET_REPORT_VERSION", auto())
    # ── external pull ─────────────────────────────────────────────────────────
    PULL_CLINICAL_EVIDENCE = ("PULL_CLINICAL_EVIDENCE", auto())
    PULL_RECRUITING_TRIALS = ("PULL_RECRUITING_TRIALS", auto())
    # ── matching ──────────────────────────────────────────────────────────────
    CLINICAL_TRIALS_MATCHING = ("CLINICAL_TRIALS_MATCHING", auto())
    # ── export ────────────────────────────────────────────────────────────────
    EXPORT_PATIENT_PARAMETERS = ("EXPORT_PATIENT_PARAMETERS", auto())
    EXPORT_TREATMENTS = ("EXPORT_TREATMENTS", auto())
    EXPORT_TREATMENT_SETTINGS = ("EXPORT_TREATMENT_SETTINGS", auto())
    EXPORT_RECRUITING_TRIALS = ("EXPORT_RECRUITING_TRIALS", auto())
    EXPORT_CLINICAL_EVIDENCE = ("EXPORT_CLINICAL_EVIDENCE", auto())
    EXPORT_CONTRAINDICATIONS = ("EXPORT_CONTRAINDICATIONS", auto())
    EXPORT_THERAPY_NODE = ("EXPORT_THERAPY_NODE", auto())
    EXPORT_SOMATIC_MUTATIONS = ("EXPORT_SOMATIC_MUTATIONS", auto())
    EXPORT_GERMLINE_MUTATIONS = ("EXPORT_GERMLINE_MUTATIONS", auto())
    EXPORT_HLA_ALLELES = ("EXPORT_HLA_ALLELES", auto())
    EXPORT_SEGMENT_COPY_NUMBER_ALTERATIONS = ("EXPORT_SEGMENT_COPY_NUMBER_ALTERATIONS", auto())
    EXPORT_EXON_COPY_NUMBER_ALTERATIONS = ("EXPORT_EXON_COPY_NUMBER_ALTERATIONS", auto())
    EXPORT_LOH_COPY_NUMBER_ALTERATIONS = ("EXPORT_LOH_COPY_NUMBER_ALTERATIONS", auto())
    EXPORT_CE_PRESETS = ("EXPORT_CE_PRESETS", auto())
    EXPORT_OCT_PRESETS = ("EXPORT_OCT_PRESETS", auto())
    EXPORT_REARRANGEMENTS = ("EXPORT_REARRANGEMENTS", auto())
    EXPORT_FUSIONS = ("EXPORT_FUSIONS", auto())
    EXPORT_GENESETS = ("EXPORT_GENESETS", auto())
    EXPORT_BIOLOGICAL_PROCESSES = ("EXPORT_BIOLOGICAL_PROCESSES", auto())
    EXPORT_CELL_POPULATIONS = ("EXPORT_CELL_POPULATIONS", auto())
    EXPORT_COPY_NUMBER_ALTERATIONS = ("EXPORT_COPY_NUMBER_ALTERATIONS", auto())
    EXPORT_GENE_EXPRESSIONS = ("EXPORT_GENE_EXPRESSIONS", auto())
    EXPORT_COMPLEX_MEASURES = ("EXPORT_COMPLEX_MEASURES", auto())
    EXPORT_SUPERBIOMARKERS = ("EXPORT_SUPERBIOMARKERS", auto())
    EXPORT_SIGNALING_BIOMARKERS = ("EXPORT_SIGNALING_BIOMARKERS", auto())
    # ── sync ──────────────────────────────────────────────────────────────────
    SYNC_OCT_TREATMENTS = ("SYNC_OCT_TREATMENTS", auto())
    # ── push ──────────────────────────────────────────────────────────────────
    PUSH_MATCHED_TREATMENTS = ("PUSH_MATCHED_TREATMENTS", auto())
    PUSH_TREATMENT_SETTINGS = ("PUSH_TREATMENT_SETTINGS", auto())
    PUSH_SIGNALING_BIOMARKERS = ("PUSH_SIGNALING_BIOMARKERS", auto())
    PUSH_MATCHED_CONTRAINDICATIONS = ("PUSH_MATCHED_CONTRAINDICATIONS", auto())
    PUSH_SOMATIC_MUTATIONS = ("PUSH_SOMATIC_MUTATIONS", auto())
    PUSH_GERMLINE_MUTATIONS = ("PUSH_GERMLINE_MUTATIONS", auto())
    PUSH_REARRANGEMENTS = ("PUSH_REARRANGEMENTS", auto())
    PUSH_FUSIONS = ("PUSH_FUSIONS", auto())
    PUSH_GENESETS = ("PUSH_GENESETS", auto())
    PUSH_COPY_NUMBER_ALTERATIONS = ("PUSH_COPY_NUMBER_ALTERATIONS", auto())
    PUSH_GENE_EXPRESSIONS = ("PUSH_GENE_EXPRESSIONS", auto())
    PUSH_COMPLEX_MEASURES = ("PUSH_COMPLEX_MEASURES", auto())
    PUSH_CLINICAL_EVIDENCE = ("PUSH_CLINICAL_EVIDENCE", auto())
    PUSH_SUPERBIOMARKERS = ("PUSH_SUPERBIOMARKERS", auto())
    PUSH_CLINICAL_TRIALS = ("PUSH_CLINICAL_TRIALS", auto())
    PUSH_THERAPY_NODE = ("PUSH_THERAPY_NODE", auto())
    # ── finalise ──────────────────────────────────────────────────────────────
    REFRESH_INDEXES = ("REFRESH_INDEXES", auto())

    def __new__(cls, value: str, order: int) -> TaskSpecificationId:
        obj = str.__new__(cls, value)
        obj._value_ = value
        setattr(obj, "_order", order)
        return obj

    @property
    def order(self) -> int:
        return getattr(self, "_order", 0)


@dataclass(frozen=True)
class TaskSpecification:
    id: TaskSpecificationId
    label: str
    description: str
    depends_on: list[TaskSpecificationId]

    def match(self, task_id: TaskSpecificationId) -> bool:
        return self.id is task_id

    def is_dependent(self, task_id: TaskSpecificationId) -> bool:
        return any(req is task_id for req in self.depends_on)

    def merge(self, updated: TaskSpecification) -> TaskSpecification:
        return replace(self, label=updated.label, description=updated.description, depends_on=updated.depends_on)
