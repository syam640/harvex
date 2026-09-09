"""Pydantic schemas for AI response validation."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SuitabilityLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class IrrigationRecommendation(str, Enum):
    IRRIGATE_NOW = "IRRIGATE_NOW"
    DELAY = "DELAY"
    MONITOR = "MONITOR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ImageQuality(str, Enum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNCLEAR = "unclear"


# ---- Crop Recommendation ----

class CropAlternative(BaseModel):
    crop: str
    suitability: SuitabilityLevel
    reasons: list[str] = []
    limiting_factors: list[str] = []


class CropRecommendationResult(BaseModel):
    recommended_crop: str
    suitability: SuitabilityLevel = SuitabilityLevel.MEDIUM
    reasons: list[str] = []
    favorable_factors: list[str] = []
    limiting_factors: list[str] = []
    water_requirement: str = "medium"
    climate_suitability: SuitabilityLevel = SuitabilityLevel.MEDIUM
    major_risks: list[str] = []
    uncertainties: list[str] = []
    alternatives: list[CropAlternative] = []


# ---- Disease Analysis ----

class DiseaseAnalysisResult(BaseModel):
    crop: str
    health_status: str = "unable_to_determine"
    disease_name: str = "Unable to determine"
    severity: str = "unknown"
    confidence: Optional[float] = None
    visual_evidence: list[str] = []
    explanation: str = ""
    needs_follow_up: bool = False
    needs_better_image: bool = False
    # Legacy field aliases for backward compatibility
    diagnosis: Optional[str] = None
    plant_health: Optional[str] = None
    visual_symptoms: Optional[list[str]] = None


# ---- Treatment ----

class TreatmentResult(BaseModel):
    immediate_actions: list[str] = []
    cultural_or_organic_actions: list[str] = []
    chemical_options: list[str] = []
    precautions: list[str] = []
    follow_up_days: int = 3
    reassessment_reason: str = ""
    safety_note: str = "Follow product label and local agricultural guidance."
    uncertainty_note: str = ""
    # Legacy field aliases
    cultural_practices: Optional[list[str]] = None
    sanitation: Optional[list[str]] = None
    biological_options: Optional[list[str]] = None
    chemical_control: Optional[list[str]] = None
    safety_precautions: Optional[list[str]] = None


# ---- Risk ----

class RiskComponent(BaseModel):
    level: RiskLevel = RiskLevel.UNKNOWN
    drivers: list[str] = []
    evidence: list[str] = []
    uncertainty: str = ""


class RiskAnalysisResult(BaseModel):
    disease_fungal_risk: RiskComponent = RiskComponent()
    heat_stress_risk: RiskComponent = RiskComponent()
    heavy_rain_risk: RiskComponent = RiskComponent()
    water_stress_risk: RiskComponent = RiskComponent()
    wind_risk: RiskComponent = RiskComponent()
    overall_risk: RiskLevel = RiskLevel.UNKNOWN
    key_concerns: list[str] = []
    urgent_actions: list[str] = []


# ---- Irrigation ----

class IrrigationResult(BaseModel):
    recommendation: IrrigationRecommendation = IrrigationRecommendation.INSUFFICIENT_DATA
    reasons: list[str] = []
    water_deficit_assessment: str = ""
    soil_moisture_note: str = "Unavailable"
    confidence: ConfidenceLabel = ConfidenceLabel.LOW


# ---- Financial ----

class FinancialResult(BaseModel):
    total_cost: float = 0.0
    total_revenue: float = 0.0
    net_profit: float = 0.0
    profit_margin: str = "N/A"
    largest_expense_category: str = ""
    financial_health: str = "moderate"
    key_insights: list[str] = []
    recommendations: list[str] = []


# ---- What-If ----

class WhatIfEffect(BaseModel):
    factor: str
    impact: str
    direction: str = "neutral"


class WhatIfResult(BaseModel):
    scenario_name: str = ""
    impact_summary: str = ""
    score_change: str = ""
    effects: list[WhatIfEffect] = []
    recommendations: list[str] = []
    uncertainties: list[str] = []


# ---- Farm Insight ----

class FarmInsight(BaseModel):
    category: str = "general"
    title: str = ""
    description: str = ""
    priority: str = "medium"
    source: str = ""


class FarmInsightResult(BaseModel):
    insights: list[FarmInsight] = []
    summary: str = ""


# ---- AI Unavailable ----

class AIUnavailableResponse(BaseModel):
    available: bool = False
    error_code: str = "AI_PROVIDER_UNAVAILABLE"
    message: str = "AI analysis is temporarily unavailable. Core farm intelligence remains available."
