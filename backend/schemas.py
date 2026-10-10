"""Request and response shapes. FastAPI lists them on the /docs page."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Eye = Literal["right", "left"]
Result = Literal["no_concern", "refer", "uncertain"]


class LoginIn(BaseModel):
    email: str
    password: str


class User(BaseModel):
    id: int
    name: str
    role: str
    email: str


class LoginOut(BaseModel):
    user: User
    token: str = Field(description="Also set as a cookie; only needed by scripts that cannot keep cookies")


class PatientIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=120)
    sex: Literal["female", "male", "other"]
    phone: Optional[str] = None
    email: Optional[str] = None


class Patient(PatientIn):
    id: str = Field(examples=["P-001"])
    created_at: str


class NextId(BaseModel):
    id: str = Field(examples=["P-005"])


class Image(BaseModel):
    id: str = Field(examples=["IMG-0001"])
    patient_id: str
    eye: Eye
    file_name: str = Field(examples=["P-001_right.jpg"])
    width: Optional[int]
    height: Optional[int]
    quality_status: Literal["passed", "failed"]
    quality_reason: Optional[Literal["unreadable", "too_dark", "not_fundus"]]
    quality_message: Optional[str] = Field(description="Alert title for a failed check")
    uploaded_at: str
    url: Optional[str] = Field(description="512 x 512 preprocessed photo (Results thumbnail)")
    original_url: Optional[str]


class ConditionResult(BaseModel):
    condition: Literal["cataract", "glaucoma"]
    raw_score: float
    calibrated_score: float = Field(description="Risk score 0 to 1; Results hides it when uncertain")
    threshold: float
    result: Result
    flag_reason: str
    heatmap_id: Optional[str]
    heatmap_url: Optional[str]


class ModelVersion(BaseModel):
    id: str = Field(examples=["v0-mock"])
    thresholds: dict[str, float]
    uncertain_margin: float
    commit: Optional[str] = Field(description="Set by Task 19; never show a made-up hash")
    is_mock: bool
    released_at: str


class Screening(BaseModel):
    id: str = Field(examples=["SCR-0001"])
    created_at: str
    created_by: str
    patient: Patient
    eye: Eye
    skipped: bool
    skip_reason: Optional[str]
    overall_result: Optional[Literal["no_concern", "refer"]] = Field(description="None when the eye was skipped")
    image: Optional[Image]
    conditions: list[ConditionResult]
    model_version: Optional[ModelVersion]


class ScreeningIn(BaseModel):
    patient_id: str
    eye: Eye
    image_id: Optional[str] = Field(None, description="Required unless skipped")
    skipped: bool = False
    skip_reason: Optional[str] = Field(None, description="Required when skipped")


class ScreeningSummary(BaseModel):
    id: str
    created_at: str
    patient_id: str
    patient_name: str
    eye: Eye
    skipped: bool
    skip_reason: Optional[str]
    overall_result: Optional[Literal["no_concern", "refer"]]
    cataract: Optional[Result]
    glaucoma: Optional[Result]


class LatestPerEye(BaseModel):
    right: Optional[Screening]
    left: Optional[Screening]


class PatientDetail(BaseModel):
    patient: Patient
    last_encounter: Optional[str]
    latest: LatestPerEye
