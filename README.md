# HARVEX — Farm Decision Intelligence Platform

AI-powered farm decision intelligence platform that combines machine learning, weather data, and farm context into actionable recommendations.

## Problem

Farmers face complex decisions about crop selection, disease management, irrigation timing, and resource allocation. Traditional farming relies on intuition and experience, leading to suboptimal outcomes.

## Solution
 
Harvex integrates:
- **Crop Recommendation** — ML-based crop suitability analysis (RandomForest, 99.55% accuracy, 22 crops)
- **Disease Detection** — Real-time plant disease identification (MobileNetV2, 88.2% accuracy, 10 tomato diseases)
- **Weather Intelligence** — OpenWeather API with agricultural risk signals
- **Decision Engine** — Multi-factor weighted scoring (Profit/Risk/Cost/Water/Sustainability)
- **Scenario Comparison** — What-if analysis for farm decisions
- **Expense Tracking** — Cultivation cost management
- **Harvest Recording** — Yield and profitability tracking
- **AI Assistant** — Context-aware farm guidance (Ollama)
- **Bilingual** — English/Telugu language support

## Architecture

```
React/Vite Frontend (TypeScript + Tailwind)
        ↓ proxy
    FastAPI Backend (Python)
        ↓
   SQLAlchemy ORM
        ↓
   SQLite (dev) / PostgreSQL (prod)
        ↓
   External APIs: OpenWeather, Ollama
```

## Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite 5
- Tailwind CSS
- React Router
- Axios

**Backend:**
- Python 3.14+
- FastAPI
- SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- Pydantic v2
- JWT (bcrypt + python-jose)

**ML:**
- PyTorch + torchvision (Disease Detection — MobileNetV2 transfer learning)
- scikit-learn (Crop Recommendation — RandomForest)
- joblib (model serialization)

**Database:**
- SQLite for development
- PostgreSQL for production (configurable via DATABASE_URL)

## ML Models

### Crop Recommendation
- **Algorithm:** RandomForest Classifier (200 estimators)
- **Features:** N, P, K, temperature, humidity, pH, rainfall
- **Dataset:** [Crop Recommendation Dataset](https://raw.githubusercontent.com/nileshiq/Crop-Recommendation/main/Crop_Recommendation.csv) (2200 samples, 22 crops)
- **Test Accuracy:** 99.55% (stratified 80/20 split)
- **CV Accuracy:** 99.45% ± 0.23% (5-fold)
- **Model version:** `crop_rf_v1_20260907`
- **Artifact:** `backend/app/ml/models/crop_model.joblib`

### Disease Detection
- **Algorithm:** MobileNetV2 (transfer learning from ImageNet)
- **Classes:** 10 tomato diseases
  - Bacterial Spot, Early Blight, Late Blight, Leaf Mold
  - Septoria Leaf Spot, Spider Mites, Target Spot
  - Yellow Leaf Curl Virus, Mosaic Virus, Healthy
- **Dataset:** [PlantVillage Dataset](https://github.com/spMohanty/PlantVillage-Dataset) (tomato subset, 502 images)
- **Test Accuracy:** 88.2%
- **Macro F1:** 0.87
- **Model version:** `disease_pth_v1_20260907`
- **Artifact:** `backend/app/ml/models/disease_model.pth`

## Running Locally

### Prerequisites
- Python 3.14+
- Node.js 18+

### Backend Setup

```bash
cd backend

# Install dependencies (system-wide, no venv needed on this machine)
pip install --break-system-packages -r requirements.txt

# Environment variables (already configured)
# DATABASE_URL=sqlite:///./harvex.db

# Train crop model
python app/ml/train_crop_model.py

# Train disease model (downloads PlantVillage automatically)
python app/ml/train_disease_model.py

# Run server
python -m uvicorn main:app --port 8001
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev    # runs on port 5173, proxies to backend 8001
```

## Environment Variables

See `.env.example` for full configuration:

```env
# Database (SQLite for dev, PostgreSQL for prod)
DATABASE_URL=sqlite:///./harvex.db

# JWT Authentication
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# OpenWeather API (https://openweathermap.org/api)
OPENWEATHER_API_KEY=your_api_key_here

# AI Assistant (Ollama)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# File Storage
UPLOAD_DIR=./storage/uploads
MAX_UPLOAD_SIZE_MB=10
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login, get JWT |
| `/api/auth/me` | GET | Get current user |
| `/api/farms` | GET/POST | List/create farms |
| `/api/farms/{id}/fields` | GET/POST | List/create fields |
| `/api/crop-cycles` | POST | Create crop cycle |
| `/api/crop/recommend` | POST | Get crop recommendation |
| `/api/disease/scan` | POST | Upload leaf image for disease detection |
| `/api/weather/current` | GET | Current weather + agricultural signals |
| `/api/decision/analyze` | POST | Multi-factor decision analysis |
| `/api/scenarios` | GET/POST | Scenario comparison |
| `/api/crop-cycles/{id}/expenses` | GET/POST | Expense tracking |
| `/api/crop-cycles/{id}/harvests` | GET/POST | Harvest recording |
| `/api/crop-cycles/{id}/prediction-vs-reality` | GET | Yield prediction vs actual |
| `/api/assistant/chat` | POST | AI assistant (English/Telugu) |

## Security

- JWT-based authentication with bcrypt password hashing
- All resource endpoints verify `Farm.user_id == current_user.id`
- Cross-user access returns 404 (not 403) to prevent resource enumeration
- Uploaded files stored per-user directory

## Weather Configuration

Requires an OpenWeather API key:
1. Sign up at https://openweathermap.org/api
2. Get a free API key
3. Set `OPENWEATHER_API_KEY` in `.env`
4. Without a key, weather endpoint returns 503 with clear message

## AI Assistant Setup

### Ollama (Optional)

```bash
# Install Ollama (requires sudo)
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.2
```

Without Ollama, the assistant returns a graceful "unavailable" message.

## Testing

### Decision Engine Unit Tests
```bash
cd backend
python -m pytest tests/test_decision_engine.py
```

### E2E API Tests
```bash
# All 22 tests must pass
# Register, Login, Farm/Field/CropCycle CRUD, Crop Recommendation,
# Disease Detection, Weather, Decision, Scenario, Expense, Harvest,
# Prediction vs Reality, Assistant (EN/TE), Security (duplicate,
# wrong password, unauthorized, cross-user isolation)
```

## Known Limitations

- SQLite for development (PostgreSQL requires server + credentials)
- Ollama requires sudo to install (unavailable without root access)
- Disease model trained on 502 images (larger dataset would improve accuracy)
- Weather requires a real OpenWeather API key
- Single farm/field per user in current UI (database supports multi-farm)
- No satellite imagery or NDVI
- No real-time IoT sensor integration
- No market price intelligence

## Project Structure

```
harvex/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── app/
│   │   ├── core/                  # config, database, security, auth
│   │   ├── api/                   # 11 API route modules
│   │   ├── models/                # SQLAlchemy models (12 tables)
│   │   ├── schemas/               # Pydantic v2 schemas
│   │   └── ml/                    # ML training + models
│   │       ├── models/            # Trained model artifacts
│   │       └── data/              # Training datasets
│   └── tests/                     # Unit tests
├── frontend/
│   ├── src/
│   │   ├── pages/                 # 12 React pages
│   │   ├── contexts/              # Auth, Farm, Language contexts
│   │   ├── layouts/               # Sidebar + top nav
│   │   └── services/              # API client with JWT
│   └── dist/                      # Production build
├── .env                           # Environment (not committed)
├── .env.example                   # Template
└── .gitignore
```

## License

MIT License
