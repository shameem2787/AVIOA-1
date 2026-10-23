from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class EvidenceItem(BaseModel):
    id: str
    label: str
    excerpt: str = ""
    source: str = "Incident report"
    page: Optional[int] = None
    relevance: str = "Relevant"

class CapaAction(BaseModel):
    id: str
    type: Literal["Corrective", "Preventive", "Effectiveness check"] = "Corrective"
    action: str
    rationale: str = ""
    owner: str = "Quality team"
    due_date: str = ""
    status: str = "Proposed"
    success_criteria: str = ""

class RootCause(BaseModel):
    id: str
    category: str = "Method"
    cause: str
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "Low"
    status: str = "Hypothesis"

class WhyStep(BaseModel):
    question: str
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)

class Investigation(BaseModel):
    id: Optional[int] = None
    title: str = "Untitled investigation"
    deviation_id: str = ""
    batch_number: str = ""
    product_name: str = ""
    process_step: str = ""
    incident_date: str = ""
    severity: str = "Major"
    status: str = "Draft"
    description: str = ""
    expected_result: str = ""
    actual_result: str = ""
    immediate_actions: str = ""
    impact_assessment: str = ""
    investigation_method: str = "5 Whys"
    timeline: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    five_whys: list[WhyStep] = Field(default_factory=list)
    fishbone: dict[str, list[str]] = Field(default_factory=dict)
    root_causes: list[RootCause] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    capa_actions: list[CapaAction] = Field(default_factory=list)
    ai_summary: str = ""
    reviewer: str = ""
    review_notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AnalyzeTextRequest(BaseModel):
    text: str = Field(min_length=10, max_length=100000)
    source_name: str = "Pasted incident text"
    source_type: str = "text"

class ReviewRequest(BaseModel):
    reviewer: str
    decision: Literal["In review", "Reviewed", "Approved", "Rejected"]
    notes: str = ""
