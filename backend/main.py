import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api import auth, farms, crop, disease, weather, decision, expenses, harvest, insights, scenarios, assistant
from app.api import ai, locations, crop_recommendations

import app.models.models  # noqa: F401 — ensure all models are registered with Base.metadata

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(levelname)s: %(message)s")
logger = logging.getLogger("harvex.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("HARVEX_STARTUP_DB_INIT_BEGIN", flush=True)

    try:
        Base.metadata.create_all(bind=engine)
        dialect = engine.url.drivername
        table_count = len(Base.metadata.tables)
        print(f"DB dialect: {dialect}, tables: {table_count}", flush=True)
        print("HARVEX_STARTUP_DB_INIT_SUCCESS", flush=True)
    except Exception as e:
        print(f"HARVEX_STARTUP_DB_INIT_FAILED: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise

    yield

    print("HARVEX_STARTUP_SHUTDOWN", flush=True)


app = FastAPI(
    title="Harvex API",
    description="AI-powered Farm Decision Intelligence Platform",
    version="2.0.0",
    lifespan=lifespan,
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


@app.get("/")
def root():
    return {"message": "Welcome to Harvex API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
