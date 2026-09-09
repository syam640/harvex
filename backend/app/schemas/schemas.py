from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    preferred_language: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class FarmCreate(BaseModel):
    name: str
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area: Optional[float] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Farm name must not be empty or whitespace')
        return v

class FarmResponse(BaseModel):
    id: int
    name: str
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    area: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class FieldCreate(BaseModel):
    name: str
    area: Optional[float] = None
    soil_type: Optional[str] = None

class FieldResponse(BaseModel):
    id: int
    farm_id: int
    name: str
    area: Optional[float]
    soil_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CropCycleCreate(BaseModel):
    field_id: int
    crop_name: str
    planting_date: datetime
    expected_harvest_date: Optional[datetime] = None

class CropCycleResponse(BaseModel):
    id: int
    field_id: int
    crop_name: str
    planting_date: datetime
    expected_harvest_date: Optional[datetime]
    status: str
    predicted_yield: Optional[float]
    predicted_yield_unit: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CropRecommendationRequest(BaseModel):
    n: float
    p: float
    k: float
    temperature: float
    humidity: float
    ph: float
    rainfall: float
    region: Optional[str] = None
    season: Optional[str] = None
    soil_type: Optional[str] = None
    water_availability: Optional[str] = None
    n_measured: Optional[bool] = False
    p_measured: Optional[bool] = False
    k_measured: Optional[bool] = False
    ph_measured: Optional[bool] = False

class CropRecommendationResponse(BaseModel):
    recommended_crop: str
    suitability_score: float
    alternatives: List[dict]
    model_version: str
    input_data: dict
    categories: Optional[dict] = None
    primary_reasons: Optional[List[str]] = None

class DiseaseScanResponse(BaseModel):
    supported: bool = True
    crop: Optional[str] = None
    health_status: Optional[str] = None
    predicted_disease: Optional[str] = None
    display_name: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None
    model_version: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    visual_evidence: Optional[List[str]] = None
    explanation: Optional[str] = None
    needs_follow_up: Optional[bool] = None
    needs_better_image: Optional[bool] = None
    top_predictions: Optional[List[dict]] = None
    quality_check: Optional[dict] = None
    actions: Optional[dict] = None
    treatment: Optional[dict] = None
    description: Optional[str] = None
    progression: Optional[str] = None
    crop_impact: Optional[str] = None
    message: Optional[str] = None

class WeatherLocation(BaseModel):
    name: str
    lat: float
    lon: float

class WeatherCurrent(BaseModel):
    temperature: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    condition: Optional[str] = None
    description: Optional[str] = None
    observed_at: Optional[str] = None

class AgriculturalSignal(BaseModel):
    level: str
    reason: str

class WeatherResponse(BaseModel):
    location: Optional[WeatherLocation] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current: Optional[WeatherCurrent] = None
    forecast: list = []
    agricultural_signals: dict = {}
    source: str
    cached: bool = False
    cache_age_minutes: int = 0
    fetched_at: Optional[str] = None

class DecisionRequest(BaseModel):
    crop_cycle_id: int

class DecisionResponse(BaseModel):
    recommended_action: str
    overall_score: float
    component_scores: dict
    reasoning: dict

class ScenarioCreate(BaseModel):
    crop_cycle_id: int
    scenario_name: str
    input_changes: dict

class ScenarioResponse(BaseModel):
    id: int
    scenario_name: str
    overall_score: float
    component_scores: dict = {}
    recommendation: str
    created_at: datetime

    class Config:
        from_attributes = True

    @staticmethod
    def from_scenario(scenario):
        return ScenarioResponse(
            id=scenario.id,
            scenario_name=scenario.scenario_name,
            overall_score=scenario.overall_score,
            component_scores={
                "profit": scenario.profit_score,
                "risk": scenario.risk_score,
                "water": scenario.water_score,
                "cost": scenario.cost_score,
                "sustainability": getattr(scenario, "sustainability_score", 0),
            },
            recommendation=scenario.recommendation,
            created_at=scenario.created_at,
        )

class ExpenseCreate(BaseModel):
    category: str
    amount: float
    description: Optional[str] = None
    expense_date: datetime

class ExpenseResponse(BaseModel):
    id: int
    crop_cycle_id: int
    category: str
    amount: float
    description: Optional[str]
    expense_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class HarvestCreate(BaseModel):
    harvest_date: datetime
    quantity: float
    unit: Optional[str] = "kg"
    selling_price: Optional[float] = None
    buyer: Optional[str] = None
    market: Optional[str] = None

class HarvestResponse(BaseModel):
    id: int
    crop_cycle_id: int
    harvest_date: datetime
    quantity: float
    unit: Optional[str]
    selling_price: Optional[float]
    buyer: Optional[str]
    market: Optional[str]
    revenue: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @staticmethod
    def compute_revenue(quantity: float, selling_price: Optional[float]) -> Optional[float]:
        if selling_price is not None and quantity is not None:
            return quantity * selling_price
        return None

class PredictionVsRealityResponse(BaseModel):
    predicted_yield: Optional[float]
    actual_yield: Optional[float]
    difference: Optional[float]
    percentage_deviation: Optional[float]
    has_prediction: bool
    total_revenue: float = 0.0
    total_cost: float = 0.0
    net_profit: Optional[float] = None
    harvest_count: int = 0
    expense_count: int = 0

class AssistantRequest(BaseModel):
    question: str
    language: str = "en"

class AssistantResponse(BaseModel):
    answer: str
    language: str
    source: str = "ai"
    model: Optional[str] = None
