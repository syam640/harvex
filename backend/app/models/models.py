from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

class CropCycleStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    preferred_language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farms = relationship("Farm", back_populates="user")

class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    location_name = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    area = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm")

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    name = Column(String(100), nullable=False)
    area = Column(Float)
    soil_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm = relationship("Farm", back_populates="fields")
    crop_cycles = relationship("CropCycle", back_populates="field")

class CropCycle(Base):
    __tablename__ = "crop_cycles"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    planting_date = Column(DateTime, nullable=False)
    expected_harvest_date = Column(DateTime)
    status = Column(String(20), default=CropCycleStatus.ACTIVE.value)
    predicted_yield = Column(Float)
    predicted_yield_unit = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    field = relationship("Field", back_populates="crop_cycles")
    disease_scans = relationship("DiseaseScan", back_populates="crop_cycle")
    decisions = relationship("Decision", back_populates="crop_cycle")
    scenarios = relationship("Scenario", back_populates="crop_cycle")
    expenses = relationship("Expense", back_populates="crop_cycle")
    harvests = relationship("Harvest", back_populates="crop_cycle")

class CropPrediction(Base):
    __tablename__ = "crop_predictions"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    input_data_json = Column(JSON)
    model_version = Column(String(50))
    suitability_score = Column(Float)
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class DiseaseScan(Base):
    __tablename__ = "disease_scans"

    id = Column(Integer, primary_key=True, index=True)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id"), nullable=True)
    image_path = Column(String(500), nullable=False)
    crop_name = Column(String(50), nullable=True)
    predicted_disease = Column(String(100))
    health_status = Column(String(30), nullable=True)
    confidence = Column(Float)
    severity = Column(String(20))
    model_version = Column(String(50))
    provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    visual_evidence = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    follow_up_state = Column(String(30), nullable=True)
    treatment_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    crop_cycle = relationship("CropCycle", back_populates="disease_scans")

class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    temperature = Column(Float)
    humidity = Column(Float)
    rainfall = Column(Float)
    wind_speed = Column(Float)
    weather_condition = Column(String(100))
    forecast_json = Column(JSON)
    source = Column(String(50))
    observed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id"), nullable=False)
    recommended_action = Column(String(500))
    score = Column(Float)
    profit_score = Column(Float)
    risk_score = Column(Float)
    cost_score = Column(Float)
    water_score = Column(Float)
    sustainability_score = Column(Float)
    reasoning_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    crop_cycle = relationship("CropCycle", back_populates="decisions")

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id"), nullable=False)
    scenario_name = Column(String(100))
    input_changes_json = Column(JSON)
    profit_score = Column(Float)
    risk_score = Column(Float)
    water_score = Column(Float)
    cost_score = Column(Float)
    sustainability_score = Column(Float)
    overall_score = Column(Float)
    recommendation = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    crop_cycle = relationship("CropCycle", back_populates="scenarios")

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id"), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(500))
    expense_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    crop_cycle = relationship("CropCycle", back_populates="expenses")

class Harvest(Base):
    __tablename__ = "harvests"

    id = Column(Integer, primary_key=True, index=True)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id"), nullable=False)
    harvest_date = Column(DateTime, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20))
    selling_price = Column(Float)
    buyer = Column(String(100))
    market = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    crop_cycle = relationship("CropCycle", back_populates="harvests")

class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id"))
    question = Column(Text)
    answer = Column(Text)
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
