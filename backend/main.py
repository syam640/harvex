import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api import auth, farms, crop, disease, weather, decision, expenses, harvest, insights, scenarios, assistant
from app.api import ai, locations, crop_recommendations

app = FastAPI(
    title="Harvex API",
    description="AI-powered Farm Decision Intelligence Platform",
    version="2.0.0"
)

cors_origins_str = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(farms.router)
app.include_router(crop.router)
app.include_router(disease.router)
app.include_router(weather.router)
app.include_router(decision.router)
app.include_router(expenses.router)
app.include_router(harvest.router)
app.include_router(insights.router)
app.include_router(scenarios.router)
app.include_router(assistant.router)
app.include_router(ai.router)
app.include_router(locations.router)
app.include_router(crop_recommendations.router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Welcome to Harvex API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
