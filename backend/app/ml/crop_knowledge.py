"""
HARVEX Crop Knowledge Base v2
Structured agricultural reference data for 22 crops supported by the ML model.

Architecture:
- CROP_REGISTRY: canonical identity system (model_label → canonical_id → display_name)
- CROP_KNOWLEDGE: agronomic data per crop (ranges, not fixed values)
- NPK_RANGES: legitimate N/P/K requirement ranges per crop (kg/ha)
- Score functions: each returns 0-100 based on how well conditions match the crop's needs

Sources:
- ICAR (Indian Council of Agricultural Research) crop production guides
- FAO Crop Information databases
- State Agricultural University publications (ANGRAU, PJTSAU, ANGRAU)
- Ministry of Agriculture, Government of India crop calendars
- "Package of Practices" publications from agricultural universities

Every threshold is derived from published agronomic literature.
Do NOT invent thresholds. If uncertain, leave the field as None.
"""

from typing import Dict, List, Optional, Any, Tuple

# =============================================================================
# CANONICAL CROP IDENTITY SYSTEM
# =============================================================================

CROP_REGISTRY: Dict[str, Dict[str, str]] = {
    # model_label (from ML model) -> canonical info
    "Rice":        {"canonical_id": "rice",         "display_name": "Rice",        "category": "Cereals"},
    "Maize":       {"canonical_id": "maize",        "display_name": "Maize",       "category": "Cereals"},
    "ChickPea":    {"canonical_id": "chickpea",     "display_name": "Chickpea",    "category": "Pulses"},
    "KidneyBeans": {"canonical_id": "kidney_beans", "display_name": "Kidney Beans","category": "Pulses"},
    "PigeonPeas":  {"canonical_id": "pigeon_pea",   "display_name": "Pigeon Pea",  "category": "Pulses"},
    "MothBeans":   {"canonical_id": "moth_bean",    "display_name": "Moth Bean",   "category": "Pulses"},
    "MungBean":    {"canonical_id": "mung_bean",    "display_name": "Mung Bean",   "category": "Pulses"},
    "Blackgram":   {"canonical_id": "black_gram",   "display_name": "Black Gram",  "category": "Pulses"},
    "Lentil":      {"canonical_id": "lentil",       "display_name": "Lentil",      "category": "Pulses"},
    "Pomegranate": {"canonical_id": "pomegranate",  "display_name": "Pomegranate", "category": "Fruits"},
    "Banana":      {"canonical_id": "banana",       "display_name": "Banana",      "category": "Fruits"},
    "Mango":       {"canonical_id": "mango",        "display_name": "Mango",       "category": "Fruits"},
    "Grapes":      {"canonical_id": "grapes",       "display_name": "Grapes",      "category": "Fruits"},
    "Watermelon":  {"canonical_id": "watermelon",   "display_name": "Watermelon",  "category": "Fruits"},
    "Muskmelon":   {"canonical_id": "muskmelon",    "display_name": "Muskmelon",   "category": "Fruits"},
    "Apple":       {"canonical_id": "apple",        "display_name": "Apple",       "category": "Fruits"},
    "Orange":      {"canonical_id": "orange",       "display_name": "Orange",      "category": "Fruits"},
    "Papaya":      {"canonical_id": "papaya",       "display_name": "Papaya",      "category": "Fruits"},
    "Coconut":     {"canonical_id": "coconut",      "display_name": "Coconut",     "category": "Fruits"},
    "Cotton":      {"canonical_id": "cotton",       "display_name": "Cotton",      "category": "Commercial"},
    "Jute":        {"canonical_id": "jute",         "display_name": "Jute",        "category": "Commercial"},
    "Coffee":      {"canonical_id": "coffee",       "display_name": "Coffee",      "category": "Commercial"},
}

def get_canonical_crop(model_label: str) -> Dict[str, str]:
    """Map ML model output label to canonical crop identity."""
    return CROP_REGISTRY.get(model_label, {
        "canonical_id": model_label.lower(),
        "display_name": model_label,
        "category": "Unknown",
    })


# =============================================================================
# N/P/K REQUIREMENT RANGES (kg/ha)
# =============================================================================
# Based on ICAR recommended doses for major Indian crops.
# These are ranges, not single values, reflecting variability across
# varieties, soil types, and management practices.

NPK_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "Rice":        {"n": (80, 120), "p": (40, 60), "k": (40, 60)},
    "Maize":       {"n": (80, 120), "p": (40, 60), "k": (40, 60)},
    "Chickpea":    {"n": (20, 40),  "p": (40, 60), "k": (20, 40)},
    "KidneyBeans": {"n": (25, 50),  "p": (40, 60), "k": (30, 50)},
    "PigeonPeas":  {"n": (20, 40),  "p": (40, 60), "k": (20, 40)},
    "MothBeans":   {"n": (15, 30),  "p": (20, 40), "k": (15, 30)},
    "MungBean":    {"n": (20, 40),  "p": (30, 50), "k": (20, 40)},
    "Blackgram":   {"n": (20, 40),  "p": (30, 50), "k": (20, 40)},
    "Lentil":      {"n": (15, 30),  "p": (30, 50), "k": (15, 30)},
    "Pomegranate": {"n": (60, 100), "p": (40, 60), "k": (60, 100)},
    "Banana":      {"n": (100, 150),"p": (40, 60), "k": (80, 120)},
    "Mango":       {"n": (60, 100), "p": (30, 50), "k": (60, 100)},
    "Grapes":      {"n": (60, 100), "p": (40, 60), "k": (60, 100)},
    "Watermelon":  {"n": (60, 100), "p": (40, 60), "k": (50, 80)},
    "Muskmelon":   {"n": (60, 100), "p": (40, 60), "k": (50, 80)},
    "Apple":       {"n": (60, 100), "p": (30, 50), "k": (60, 100)},
    "Orange":      {"n": (60, 100), "p": (30, 50), "k": (60, 100)},
    "Papaya":      {"n": (80, 120), "p": (40, 60), "k": (60, 100)},
    "Coconut":     {"n": (60, 100), "p": (30, 50), "k": (80, 120)},
    "Cotton":      {"n": (60, 100), "p": (30, 50), "k": (30, 60)},
    "Jute":        {"n": (60, 100), "p": (30, 50), "k": (40, 60)},
    "Coffee":      {"n": (60, 100), "p": (30, 50), "k": (60, 100)},
}


# =============================================================================
# AGRONOMIC KNOWLEDGE BASE
# =============================================================================
# Each crop entry contains ranges and thresholds for scoring.
# Scores are 0-100 where 100 = perfect match, 0 = completely unsuitable.

CROP_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "Rice": {
        "scientific_name": "Oryza sativa",
        "preferred_temp_range": (20, 35),
        "optimal_temp": 27,
        "preferred_humidity_range": (60, 90),
        "preferred_ph_range": (5.5, 7.0),
        "water_requirement": "high",
        "rainfall_requirement_mm": (1000, 2000),
        "soil_compatibility": ["clay", "loamy", "alluvial"],
        "season_suitability": {"kharif": 0.95, "rabi": 0.3, "summer": 0.2},
        "region_suitability": {
            "coastal_andhra": 0.95, "rayalaseema": 0.7, "telangana": 0.8,
            "karnataka": 0.85, "tamil_nadu": 0.9, "odisha": 0.9,
            "maharashtra": 0.8, "other": 0.6,
        },
        "common_diseases": ["Blast", "Bacterial Leaf Blight", "Sheath Blight"],
        "crop_duration_days": (120, 150),
        "management_notes": "Standing water required for most of the growing season. Transplanting preferred.",
    },
    "Maize": {
        "scientific_name": "Zea mays",
        "preferred_temp_range": (18, 32),
        "optimal_temp": 25,
        "preferred_humidity_range": (50, 80),
        "preferred_ph_range": (5.5, 7.5),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (500, 800),
        "soil_compatibility": ["loamy", "sandy_loam", "alluvial"],
        "season_suitability": {"kharif": 0.9, "rabi": 0.7, "summer": 0.5},
        "region_suitability": {
            "coastal_andhra": 0.7, "rayalaseema": 0.8, "telangana": 0.85,
            "karnataka": 0.8, "tamil_nadu": 0.7, "odisha": 0.75,
            "maharashtra": 0.85, "other": 0.7,
        },
        "common_diseases": ["Downy Mildew", "Leaf Blight", "Stalk Rot"],
        "crop_duration_days": (80, 120),
        "management_notes": "Requires well-drained soil. Sensitive to waterlogging.",
    },
    "ChickPea": {
        "scientific_name": "Cicer arietinum",
        "preferred_temp_range": (15, 30),
        "optimal_temp": 22,
        "preferred_humidity_range": (40, 70),
        "preferred_ph_range": (6.0, 8.0),
        "water_requirement": "low",
        "rainfall_requirement_mm": (400, 600),
        "soil_compatibility": ["loamy", "clay_loam", "black"],
        "season_suitability": {"kharif": 0.2, "rabi": 0.95, "summer": 0.1},
        "region_suitability": {
            "coastal_andhra": 0.5, "rayalaseema": 0.8, "telangana": 0.75,
            "karnataka": 0.85, "tamil_nadu": 0.6, "odisha": 0.6,
            "maharashtra": 0.8, "other": 0.7,
        },
        "common_diseases": ["Wilt", "Root Rot", "Botrytis Gray Mold"],
        "crop_duration_days": (90, 120),
        "management_notes": "Rabi crop. Drought tolerant. Avoid waterlogging.",
    },
    "KidneyBeans": {
        "scientific_name": "Phaseolus vulgaris",
        "preferred_temp_range": (15, 28),
        "optimal_temp": 22,
        "preferred_humidity_range": (50, 75),
        "preferred_ph_range": (6.0, 7.5),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (600, 800),
        "soil_compatibility": ["loamy", "sandy_loam"],
        "season_suitability": {"kharif": 0.3, "rabi": 0.85, "summer": 0.2},
        "region_suitability": {
            "coastal_andhra": 0.5, "rayalaseema": 0.6, "telangana": 0.6,
            "karnataka": 0.7, "tamil_nadu": 0.55, "odisha": 0.5,
            "maharashtra": 0.65, "other": 0.6,
        },
        "common_diseases": ["Common Bacterial Blight", "Anthracnose"],
        "crop_duration_days": (90, 120),
        "management_notes": "Sensitive to frost and waterlogging.",
    },
    "PigeonPeas": {
        "scientific_name": "Cajanus cajan",
        "preferred_temp_range": (18, 35),
        "optimal_temp": 28,
        "preferred_humidity_range": (40, 70),
        "preferred_ph_range": (6.0, 7.5),
        "water_requirement": "low",
        "rainfall_requirement_mm": (400, 700),
        "soil_compatibility": ["loamy", "clay_loam", "black"],
        "season_suitability": {"kharif": 0.9, "rabi": 0.4, "summer": 0.1},
        "region_suitability": {
            "coastal_andhra": 0.6, "rayalaseema": 0.85, "telangana": 0.9,
            "karnataka": 0.85, "tamil_nadu": 0.7, "odisha": 0.65,
            "maharashtra": 0.85, "other": 0.7,
        },
        "common_diseases": ["Wilt", "Phytophthora Blight"],
        "crop_duration_days": (150, 210),
        "management_notes": "Long duration crop. Intercropped with cereals.",
    },
    "MothBeans": {
        "scientific_name": "Vigna aconitifolia",
        "preferred_temp_range": (20, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (30, 60),
        "preferred_ph_range": (6.5, 8.0),
        "water_requirement": "very_low",
        "rainfall_requirement_mm": (200, 400),
        "soil_compatibility": ["sandy", "loamy", "sandy_loam"],
        "season_suitability": {"kharif": 0.9, "rabi": 0.3, "summer": 0.1},
        "region_suitability": {
            "coastal_andhra": 0.4, "rayalaseema": 0.8, "telangana": 0.75,
            "karnataka": 0.7, "tamil_nadu": 0.5, "odisha": 0.5,
            "maharashtra": 0.8, "other": 0.6,
        },
        "common_diseases": ["Root Rot", "Powdery Mildew"],
        "crop_duration_days": (70, 90),
        "management_notes": "Extremely drought tolerant. Good for arid regions.",
    },
    "MungBean": {
        "scientific_name": "Vigna radiata",
        "preferred_temp_range": (18, 35),
        "optimal_temp": 28,
        "preferred_humidity_range": (50, 75),
        "preferred_ph_range": (6.2, 7.5),
        "water_requirement": "low",
        "rainfall_requirement_mm": (300, 600),
        "soil_compatibility": ["loamy", "sandy_loam", "alluvial"],
        "season_suitability": {"kharif": 0.8, "rabi": 0.7, "summer": 0.5},
        "region_suitability": {
            "coastal_andhra": 0.7, "rayalaseema": 0.75, "telangana": 0.8,
            "karnataka": 0.75, "tamil_nadu": 0.7, "odisha": 0.65,
            "maharashtra": 0.75, "other": 0.7,
        },
        "common_diseases": ["Yellow Mosaic Virus", "Cercospora Leaf Spot"],
        "crop_duration_days": (60, 75),
        "management_notes": "Short duration pulse. Good as intercrop.",
    },
    "Blackgram": {
        "scientific_name": "Vigna mungo",
        "preferred_temp_range": (20, 35),
        "optimal_temp": 28,
        "preferred_humidity_range": (50, 80),
        "preferred_ph_range": (6.0, 7.5),
        "water_requirement": "low",
        "rainfall_requirement_mm": (400, 700),
        "soil_compatibility": ["loamy", "clay_loam", "black"],
        "season_suitability": {"kharif": 0.85, "rabi": 0.6, "summer": 0.3},
        "region_suitability": {
            "coastal_andhra": 0.7, "rayalaseema": 0.8, "telangana": 0.8,
            "karnataka": 0.75, "tamil_nadu": 0.7, "odisha": 0.65,
            "maharashtra": 0.75, "other": 0.7,
        },
        "common_diseases": ["Yellow Mosaic Virus", "Root Rot"],
        "crop_duration_days": (70, 90),
        "management_notes": "Important pulse in rotation with rice.",
    },
    "Lentil": {
        "scientific_name": "Lens culinaris",
        "preferred_temp_range": (12, 25),
        "optimal_temp": 20,
        "preferred_humidity_range": (40, 65),
        "preferred_ph_range": (6.0, 8.0),
        "water_requirement": "low",
        "rainfall_requirement_mm": (300, 500),
        "soil_compatibility": ["loamy", "sandy_loam", "alluvial"],
        "season_suitability": {"kharif": 0.1, "rabi": 0.95, "summer": 0.05},
        "region_suitability": {
            "coastal_andhra": 0.3, "rayalaseema": 0.5, "telangana": 0.4,
            "karnataka": 0.5, "tamil_nadu": 0.3, "odisha": 0.4,
            "maharashtra": 0.45, "other": 0.5,
        },
        "common_diseases": ["Wilt", "Botrytis Gray Mold"],
        "crop_duration_days": (90, 120),
        "management_notes": "Cool season pulse. Primarily rabi in India.",
    },
    "Pomegranate": {
        "scientific_name": "Punica granatum",
        "preferred_temp_range": (18, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (30, 60),
        "preferred_ph_range": (6.0, 7.5),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (400, 600),
        "soil_compatibility": ["sandy_loam", "loamy", "red"],
        "season_suitability": {"kharif": 0.5, "rabi": 0.6, "summer": 0.7},
        "region_suitability": {
            "coastal_andhra": 0.6, "rayalaseema": 0.85, "telangana": 0.8,
            "karnataka": 0.8, "tamil_nadu": 0.7, "odisha": 0.5,
            "maharashtra": 0.8, "other": 0.7,
        },
        "common_diseases": ["Bacterial Blight", "Cercospora Fruit Spot"],
        "crop_duration_days": None,
        "management_notes": "Perennial crop. First harvest from year 3.",
    },
    "Banana": {
        "scientific_name": "Musa spp.",
        "preferred_temp_range": (15, 38),
        "optimal_temp": 28,
        "preferred_humidity_range": (60, 90),
        "preferred_ph_range": (5.5, 7.0),
        "water_requirement": "high",
        "rainfall_requirement_mm": (1000, 2000),
        "soil_compatibility": ["loamy", "clay_loam", "alluvial", "red"],
        "season_suitability": {"kharif": 0.8, "rabi": 0.7, "summer": 0.8},
        "region_suitability": {
            "coastal_andhra": 0.9, "rayalaseema": 0.7, "telangana": 0.75,
            "karnataka": 0.8, "tamil_nadu": 0.85, "odisha": 0.7,
            "maharashtra": 0.8, "other": 0.75,
        },
        "common_diseases": ["Panama Wilt", "Black Sigatoka"],
        "crop_duration_days": (270, 365),
        "management_notes": "Perennial. Requires wind protection.",
    },
    "Mango": {
        "scientific_name": "Mangifera indica",
        "preferred_temp_range": (15, 40),
        "optimal_temp": 30,
        "preferred_humidity_range": (40, 70),
        "preferred_ph_range": (5.5, 7.5),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (750, 1500),
        "soil_compatibility": ["loamy", "sandy_loam", "red", "alluvial"],
        "season_suitability": {"kharif": 0.6, "rabi": 0.5, "summer": 0.7},
        "region_suitability": {
            "coastal_andhra": 0.8, "rayalaseema": 0.85, "telangana": 0.85,
            "karnataka": 0.9, "tamil_nadu": 0.85, "odisha": 0.7,
            "maharashtra": 0.85, "other": 0.8,
        },
        "common_diseases": ["Anthracnose", "Powdery Mildew"],
        "crop_duration_days": None,
        "management_notes": "Perennial tree crop. First commercial harvest from year 5.",
    },
    "Grapes": {
        "scientific_name": "Vitis vinifera",
        "preferred_temp_range": (12, 35),
        "optimal_temp": 25,
        "preferred_humidity_range": (30, 60),
        "preferred_ph_range": (5.5, 7.0),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (500, 800),
        "soil_compatibility": ["sandy_loam", "loamy", "red"],
        "season_suitability": {"kharif": 0.6, "rabi": 0.5, "summer": 0.7},
        "region_suitability": {
            "coastal_andhra": 0.5, "rayalaseema": 0.7, "telangana": 0.65,
            "karnataka": 0.8, "tamil_nadu": 0.6, "odisha": 0.4,
            "maharashtra": 0.75, "other": 0.6,
        },
        "common_diseases": ["Downy Mildew", "Powdery Mildew"],
        "crop_duration_days": None,
        "management_notes": "Perennial vine. Requires support trellis.",
    },
    "Watermelon": {
        "scientific_name": "Citrullus lanatus",
        "preferred_temp_range": (20, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (40, 70),
        "preferred_ph_range": (6.0, 7.0),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (400, 700),
        "soil_compatibility": ["sandy", "sandy_loam", "loamy"],
        "season_suitability": {"kharif": 0.4, "rabi": 0.3, "summer": 0.9},
        "region_suitability": {
            "coastal_andhra": 0.7, "rayalaseema": 0.8, "telangana": 0.75,
            "karnataka": 0.75, "tamil_nadu": 0.8, "odisha": 0.6,
            "maharashtra": 0.75, "other": 0.7,
        },
        "common_diseases": ["Fusarium Wilt", "Anthracnose"],
        "crop_duration_days": (80, 100),
        "management_notes": "Sprawling vine. Needs space.",
    },
    "Muskmelon": {
        "scientific_name": "Cucumis melo",
        "preferred_temp_range": (18, 35),
        "optimal_temp": 28,
        "preferred_humidity_range": (40, 65),
        "preferred_ph_range": (6.0, 7.0),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (400, 600),
        "soil_compatibility": ["sandy_loam", "loamy", "sandy"],
        "season_suitability": {"kharif": 0.3, "rabi": 0.3, "summer": 0.9},
        "region_suitability": {
            "coastal_andhra": 0.65, "rayalaseema": 0.75, "telangana": 0.7,
            "karnataka": 0.7, "tamil_nadu": 0.75, "odisha": 0.55,
            "maharashtra": 0.7, "other": 0.65,
        },
        "common_diseases": ["Powdery Mildew", "Downy Mildew"],
        "crop_duration_days": (75, 90),
        "management_notes": "Warm season crop. Sensitive to frost.",
    },
    "Apple": {
        "scientific_name": "Malus domestica",
        "preferred_temp_range": (10, 28),
        "optimal_temp": 20,
        "preferred_humidity_range": (50, 75),
        "preferred_ph_range": (5.5, 6.8),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (800, 1200),
        "soil_compatibility": ["loamy", "sandy_loam", "alluvial"],
        "season_suitability": {"kharif": 0.5, "rabi": 0.6, "summer": 0.4},
        "region_suitability": {
            "coastal_andhra": 0.1, "rayalaseema": 0.1, "telangana": 0.1,
            "karnataka": 0.2, "tamil_nadu": 0.1, "odisha": 0.15,
            "maharashtra": 0.15, "other": 0.3,
        },
        "common_diseases": ["Apple Scab", "Fire Blight"],
        "crop_duration_days": None,
        "management_notes": "Temperate crop. Requires 800-1200 chill hours.",
    },
    "Orange": {
        "scientific_name": "Citrus sinensis",
        "preferred_temp_range": (15, 38),
        "optimal_temp": 28,
        "preferred_humidity_range": (40, 70),
        "preferred_ph_range": (5.5, 7.0),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (750, 1200),
        "soil_compatibility": ["loamy", "sandy_loam", "red"],
        "season_suitability": {"kharif": 0.6, "rabi": 0.6, "summer": 0.6},
        "region_suitability": {
            "coastal_andhra": 0.7, "rayalaseema": 0.75, "telangana": 0.7,
            "karnataka": 0.8, "tamil_nadu": 0.8, "odisha": 0.6,
            "maharashtra": 0.75, "other": 0.7,
        },
        "common_diseases": ["Citrus Canker", "Gummosis"],
        "crop_duration_days": None,
        "management_notes": "Perennial tree. Regular irrigation essential.",
    },
    "Papaya": {
        "scientific_name": "Carica papaya",
        "preferred_temp_range": (18, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (50, 80),
        "preferred_ph_range": (5.5, 7.0),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (600, 1200),
        "soil_compatibility": ["loamy", "sandy_loam", "alluvial"],
        "season_suitability": {"kharif": 0.7, "rabi": 0.6, "summer": 0.8},
        "region_suitability": {
            "coastal_andhra": 0.8, "rayalaseema": 0.7, "telangana": 0.7,
            "karnataka": 0.75, "tamil_nadu": 0.8, "odisha": 0.65,
            "maharashtra": 0.75, "other": 0.7,
        },
        "common_diseases": ["Papaya Ringspot Virus", "Anthracnose"],
        "crop_duration_days": (180, 270),
        "management_notes": "Short-lived perennial. First harvest from 6 months.",
    },
    "Coconut": {
        "scientific_name": "Cocos nucifera",
        "preferred_temp_range": (18, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (60, 90),
        "preferred_ph_range": (5.0, 8.0),
        "water_requirement": "high",
        "rainfall_requirement_mm": (1000, 2500),
        "soil_compatibility": ["sandy", "loamy", "alluvial", "red"],
        "season_suitability": {"kharif": 0.7, "rabi": 0.7, "summer": 0.7},
        "region_suitability": {
            "coastal_andhra": 0.85, "rayalaseema": 0.3, "telangana": 0.4,
            "karnataka": 0.7, "tamil_nadu": 0.85, "odisha": 0.6,
            "maharashtra": 0.65, "other": 0.6,
        },
        "common_diseases": ["Bud Rot", "Leaf Rot"],
        "crop_duration_days": None,
        "management_notes": "Perennial tree. Full production from year 6.",
    },
    "Cotton": {
        "scientific_name": "Gossypium spp.",
        "preferred_temp_range": (20, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (40, 80),
        "preferred_ph_range": (6.0, 8.0),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (600, 1200),
        "soil_compatibility": ["black", "clay_loam", "loamy"],
        "season_suitability": {"kharif": 0.95, "rabi": 0.2, "summer": 0.1},
        "region_suitability": {
            "coastal_andhra": 0.7, "rayalaseema": 0.85, "telangana": 0.9,
            "karnataka": 0.8, "tamil_nadu": 0.7, "odisha": 0.6,
            "maharashtra": 0.9, "other": 0.7,
        },
        "common_diseases": ["Bacterial Blight", "Fusarium Wilt"],
        "crop_duration_days": (150, 180),
        "management_notes": "BT cotton dominant. IPM critical.",
    },
    "Jute": {
        "scientific_name": "Corchorus spp.",
        "preferred_temp_range": (20, 38),
        "optimal_temp": 30,
        "preferred_humidity_range": (60, 90),
        "preferred_ph_range": (5.5, 7.5),
        "water_requirement": "high",
        "rainfall_requirement_mm": (1000, 2000),
        "soil_compatibility": ["clay", "loamy", "alluvial"],
        "season_suitability": {"kharif": 0.95, "rabi": 0.1, "summer": 0.05},
        "region_suitability": {
            "coastal_andhra": 0.6, "rayalaseema": 0.3, "telangana": 0.4,
            "karnataka": 0.4, "tamil_nadu": 0.4, "odisha": 0.8,
            "maharashtra": 0.4, "other": 0.5,
        },
        "common_diseases": ["Stem Rot", "Anthracnose"],
        "crop_duration_days": (120, 150),
        "management_notes": "Flood tolerant. Needs standing water.",
    },
    "Coffee": {
        "scientific_name": "Coffea arabica / canephora",
        "preferred_temp_range": (15, 28),
        "optimal_temp": 22,
        "preferred_humidity_range": (50, 80),
        "preferred_ph_range": (5.0, 6.5),
        "water_requirement": "medium",
        "rainfall_requirement_mm": (1000, 2000),
        "soil_compatibility": ["loamy", "red", "clay_loam"],
        "season_suitability": {"kharif": 0.6, "rabi": 0.6, "summer": 0.6},
        "region_suitability": {
            "coastal_andhra": 0.3, "rayalaseema": 0.3, "telangana": 0.2,
            "karnataka": 0.85, "tamil_nadu": 0.7, "odisha": 0.3,
            "maharashtra": 0.3, "other": 0.4,
        },
        "common_diseases": ["Coffee Leaf Rust", "Coffee Berry Disease"],
        "crop_duration_days": None,
        "management_notes": "Perennial. Shade trees important.",
    },
}


# =============================================================================
# CROP CATEGORIES
# =============================================================================

CROP_CATEGORIES = {
    "Cereals": {"crops": ["Rice", "Maize"]},
    "Pulses": {"crops": ["ChickPea", "KidneyBeans", "PigeonPeas", "MothBeans", "MungBean", "Blackgram", "Lentil"]},
    "Fruits": {"crops": ["Pomegranate", "Banana", "Mango", "Grapes", "Watermelon", "Muskmelon", "Apple", "Orange", "Papaya", "Coconut"]},
    "Commercial": {"crops": ["Cotton", "Jute", "Coffee"]},
}

REGIONS = {
    "coastal_andhra": "Coastal Andhra",
    "rayalaseema": "Rayalaseema",
    "telangana": "Telangana",
    "karnataka": "Karnataka",
    "tamil_nadu": "Tamil Nadu",
    "odisha": "Odisha",
    "maharashtra": "Maharashtra",
    "other": "Other",
}

SEASONS = {
    "kharif": "Kharif (Jun-Oct)",
    "rabi": "Rabi (Nov-Mar)",
    "summer": "Summer (Apr-May)",
}

WATER_LEVELS = {"low": 0.3, "medium": 0.6, "high": 0.9}
WATER_REQ_LEVELS = {"very_low": 0.2, "low": 0.4, "medium": 0.6, "high": 0.85}


# =============================================================================
# SCORING FUNCTIONS (each returns 0-100)
# =============================================================================

def _score_range(value: float, preferred_range: Tuple[float, float], penalty_per_unit: float = 1.0, max_penalty: float = 40.0) -> float:
    """Score how well a value fits within a preferred range.
    Returns 0-100: 100 = in range, lower = further from range.
    """
    low, high = preferred_range
    if low <= value <= high:
        return 100.0
    distance = min(abs(value - low), abs(value - high))
    penalty = min(distance * penalty_per_unit, max_penalty)
    return max(0.0, 100.0 - penalty)


def score_climate(crop_name: str, temperature: float, humidity: float, rainfall: float) -> Dict[str, Any]:
    """Score climate compatibility: temperature (40%), humidity (25%), rainfall (35%).
    Returns 0-100 and reasons."""
    info = CROP_KNOWLEDGE.get(crop_name)
    if not info:
        return {"score": 0, "reasons": ["Crop not in knowledge base"]}

    reasons = []

    # Temperature: 40% of climate score
    temp_range = info.get("preferred_temp_range", (15, 35))
    temp_score = _score_range(temperature, temp_range, penalty_per_unit=4.0, max_penalty=40.0)
    if temp_range[0] <= temperature <= temp_range[1]:
        reasons.append(f"Temperature {temperature}°C is suitable (preferred {temp_range[0]}-{temp_range[1]}°C)")
    else:
        reasons.append(f"Temperature {temperature}°C is outside preferred range ({temp_range[0]}-{temp_range[1]}°C)")

    # Humidity: 25% of climate score
    hum_range = info.get("preferred_humidity_range", (40, 80))
    hum_score = _score_range(humidity, hum_range, penalty_per_unit=2.0, max_penalty=25.0)
    if hum_range[0] <= humidity <= hum_range[1]:
        reasons.append(f"Humidity {humidity}% is suitable")
    else:
        reasons.append(f"Humidity {humidity}% is outside preferred range ({hum_range[0]}-{hum_range[1]}%)")

    # Rainfall: 35% of climate score
    rain_range = info.get("rainfall_requirement_mm", (500, 1000))
    rain_score = _score_range(rainfall, rain_range, penalty_per_unit=0.05, max_penalty=35.0)
    if rain_range[0] <= rainfall <= rain_range[1]:
        reasons.append(f"Rainfall {rainfall}mm matches requirements ({rain_range[0]}-{rain_range[1]}mm)")
    else:
        reasons.append(f"Rainfall {rainfall}mm is outside preferred range ({rain_range[0]}-{rain_range[1]}mm)")

    combined = temp_score * 0.40 + hum_score * 0.25 + rain_score * 0.35
    return {"score": round(combined, 1), "reasons": reasons}


def score_nutrients(crop_name: str, n: float, p: float, k: float) -> Dict[str, Any]:
    """Score nutrient compatibility based on ICAR recommended ranges.
    Each nutrient scored independently, then averaged.
    Returns 0-100 and reasons."""
    ranges = NPK_RANGES.get(crop_name)
    if not ranges:
        return {"score": 50.0, "reasons": ["Nutrient data not available for this crop"]}

    reasons = []

    n_range = ranges["n"]
    p_range = ranges["p"]
    k_range = ranges["k"]

    n_score = _score_range(n, n_range, penalty_per_unit=0.5, max_penalty=35.0)
    p_score = _score_range(p, p_range, penalty_per_unit=0.5, max_penalty=35.0)
    k_score = _score_range(k, k_range, penalty_per_unit=0.5, max_penalty=35.0)

    if n_range[0] <= n <= n_range[1]:
        reasons.append(f"N={n}kg/ha is within recommended range ({n_range[0]}-{n_range[1]}kg/ha)")
    else:
        reasons.append(f"N={n}kg/ha is outside recommended range ({n_range[0]}-{n_range[1]}kg/ha)")

    if p_range[0] <= p <= p_range[1]:
        reasons.append(f"P={p}kg/ha is within recommended range ({p_range[0]}-{p_range[1]}kg/ha)")
    else:
        reasons.append(f"P={p}kg/ha is outside recommended range ({p_range[0]}-{p_range[1]}kg/ha)")

    if k_range[0] <= k <= k_range[1]:
        reasons.append(f"K={k}kg/ha is within recommended range ({k_range[0]}-{k_range[1]}kg/ha)")
    else:
        reasons.append(f"K={k}kg/ha is outside recommended range ({k_range[0]}-{k_range[1]}kg/ha)")

    combined = (n_score + p_score + k_score) / 3.0
    return {"score": round(combined, 1), "reasons": reasons}


def score_soil(crop_name: str, soil_type: str, ph: float) -> Dict[str, Any]:
    """Score soil compatibility: type match (50%) + pH fit (50%).
    Returns 0-100 and reasons."""
    info = CROP_KNOWLEDGE.get(crop_name)
    if not info:
        return {"score": 0, "reasons": ["Crop not in knowledge base"]}

    reasons = []

    # Soil type: 50%
    compatible = [s.lower() for s in info.get("soil_compatibility", [])]
    if soil_type.lower() in compatible:
        soil_type_score = 100.0
        reasons.append(f"Suitable for {soil_type} soil")
    else:
        soil_type_score = 20.0
        reasons.append(f"Less ideal for {soil_type} soil (preferred: {', '.join(info.get('soil_compatibility', []))})")

    # pH: 50%
    ph_range = info.get("preferred_ph_range", (6.0, 7.5))
    ph_score = _score_range(ph, ph_range, penalty_per_unit=20.0, max_penalty=50.0)
    if ph_range[0] <= ph <= ph_range[1]:
        reasons.append(f"Soil pH {ph} is within preferred range ({ph_range[0]}-{ph_range[1]})")
    else:
        reasons.append(f"Soil pH {ph} is outside preferred range ({ph_range[0]}-{ph_range[1]})")

    combined = soil_type_score * 0.50 + ph_score * 0.50
    return {"score": round(combined, 1), "reasons": reasons}


def score_water(crop_name: str, water_availability: str) -> Dict[str, Any]:
    """Score water compatibility: compare availability to crop requirement.
    Returns 0-100 and reasons."""
    info = CROP_KNOWLEDGE.get(crop_name)
    if not info:
        return {"score": 0, "reasons": ["Crop not in knowledge base"]}

    reasons = []

    avail = WATER_LEVELS.get(water_availability, 0.6)
    needed = WATER_REQ_LEVELS.get(info.get("water_requirement", "medium"), 0.6)

    if avail >= needed:
        score = 100.0
        reasons.append(f"Water availability ({water_availability}) meets {crop_name} requirement ({info.get('water_requirement', 'medium')})")
    elif avail >= needed * 0.7:
        score = 60.0
        reasons.append(f"Water availability ({water_availability}) is marginal for {crop_name} requirement ({info.get('water_requirement', 'medium')})")
    else:
        score = 15.0
        reasons.append(f"Water availability ({water_availability}) is insufficient for {crop_name} requirement ({info.get('water_requirement', 'medium')})")

    return {"score": round(score, 1), "reasons": reasons}


def score_region(crop_name: str, region: str) -> Dict[str, Any]:
    """Score regional suitability. Returns 0-100 and reasons."""
    info = CROP_KNOWLEDGE.get(crop_name)
    if not info:
        return {"score": 0, "reasons": ["Crop not in knowledge base"]}

    reasons = []
    region_score = info.get("region_suitability", {}).get(region, 0.5)
    score = region_score * 100.0

    region_name = REGIONS.get(region, region)
    if region_score >= 0.8:
        reasons.append(f"Widely grown in {region_name}")
    elif region_score >= 0.5:
        reasons.append(f"Moderately grown in {region_name}")
    else:
        reasons.append(f"Less common in {region_name} but may grow with care")

    return {"score": round(score, 1), "reasons": reasons}


def score_season(crop_name: str, season: str) -> Dict[str, Any]:
    """Score seasonal suitability. Returns 0-100 and reasons."""
    info = CROP_KNOWLEDGE.get(crop_name)
    if not info:
        return {"score": 0, "reasons": ["Crop not in knowledge base"]}

    reasons = []
    season_score = info.get("season_suitability", {}).get(season, 0.5)
    score = season_score * 100.0

    season_name = SEASONS.get(season, season)
    if season_score >= 0.8:
        reasons.append(f"Excellent {season_name} crop")
    elif season_score >= 0.5:
        reasons.append(f"Can be grown in {season_name}")
    else:
        reasons.append(f"Not ideal for {season_name} season")

    return {"score": round(score, 1), "reasons": reasons}


# =============================================================================
# MAIN SCORING PIPELINE
# =============================================================================

# Component weights for the overall agronomic score
# These are normalized to sum to 1.0
COMPONENT_WEIGHTS = {
    "climate":    0.30,   # temperature, humidity, rainfall
    "nutrients":  0.20,   # N, P, K
    "soil":       0.20,   # soil type + pH
    "water":      0.15,   # water availability vs requirement
    "region":     0.08,   # regional context
    "season":     0.07,   # seasonal context
}


def compute_agronomic_score(
    crop_name: str,
    n: float, p: float, k: float,
    temperature: float, humidity: float, rainfall: float,
    ph: float,
    soil_type: str,
    water_availability: str,
    region: Optional[str] = None,
    season: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute a multi-component agronomic suitability score for a crop.
    
    Returns a dict with:
    - overall_score: 0-100 (weighted sum of components)
    - component_scores: dict of component name -> score
    - all_reasons: dict of component name -> list of reasons
    - limiting_factors: list of components scoring below 40
    """
    climate = score_climate(crop_name, temperature, humidity, rainfall)
    nutrients = score_nutrients(crop_name, n, p, k)
    soil = score_soil(crop_name, soil_type, ph)
    water = score_water(crop_name, water_availability)

    components = {
        "climate": climate["score"],
        "nutrients": nutrients["score"],
        "soil": soil["score"],
        "water": water["score"],
    }
    all_reasons = {
        "climate": climate["reasons"],
        "nutrients": nutrients["reasons"],
        "soil": soil["reasons"],
        "water": water["reasons"],
    }

    # Region/season are optional contextual modifiers
    if region:
        reg = score_region(crop_name, region)
        components["region"] = reg["score"]
        all_reasons["region"] = reg["reasons"]
    else:
        components["region"] = 50.0  # neutral when not provided
        all_reasons["region"] = ["Region not specified"]

    if season:
        sea = score_season(crop_name, season)
        components["season"] = sea["score"]
        all_reasons["season"] = sea["reasons"]
    else:
        components["season"] = 50.0
        all_reasons["season"] = ["Season not specified"]

    # Weighted sum
    overall = 0.0
    for comp_name, weight in COMPONENT_WEIGHTS.items():
        overall += components[comp_name] * weight

    # Identify limiting factors (score < 40)
    limiting = [name for name, score in components.items() if score < 40]

    return {
        "overall_score": round(overall, 1),
        "component_scores": {k: round(v, 1) for k, v in components.items()},
        "all_reasons": all_reasons,
        "limiting_factors": limiting,
    }


def get_crop_info(crop_name: str) -> Optional[Dict[str, Any]]:
    """Get crop knowledge info by model label."""
    return CROP_KNOWLEDGE.get(crop_name)
