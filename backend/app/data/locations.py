"""Indian location hierarchy data for HARVEX.
States → Districts → Mandals → Towns/Villages
Focus on Andhra Pradesh and Telangana with major districts."""

STATES = {
    "andhra_pradesh": {
        "en": "Andhra Pradesh",
        "te": "ఆంధ్రప్రదేశ్",
        "districts": {
            "east_godavari": {
                "en": "East Godavari",
                "te": "తూర్పు గోదావరి",
                "mandals": {
                    "peddapuram": {
                        "en": "Peddapuram",
                        "te": "పెద్దాపురం",
                        "towns": ["Peddapuram", "Kirlampudi", "Tallarevu"]
                    },
                    "kakinada": {
                        "en": "Kakinada",
                        "te": "కాకినాడ",
                        "towns": ["Kakinada", "Cocanada", "Jagannadhapuram"]
                    },
                    "ramachandrapuram": {
                        "en": "Ramachandrapuram",
                        "te": "రామచంద్రపురం",
                        "towns": ["Ramachandrapuram", "Mandapeta"]
                    },
                    "ampolu": {
                        "en": "Ampolu",
                        "te": "ఆంపోలు",
                        "towns": ["Ampolu"]
                    },
                    "prathipadu": {
                        "en": "Prathipadu",
                        "te": "ప్రతిపాడు",
                        "towns": ["Prathipadu"]
                    },
                    "gollaprolu": {
                        "en": "Gollaprolu",
                        "te": "గొల్లప్రోలు",
                        "towns": ["Gollaprolu"]
                    },
                    "pithapuram": {
                        "en": "Pithapuram",
                        "te": "పిఠాపురం",
                        "towns": ["Pithapuram", "Samarlakota"]
                    },
                    "sankhavaram": {
                        "en": "Sankhavaram",
                        "te": "సంకవరం",
                        "towns": ["Sankhavaram"]
                    },
                    "yelahanka": {
                        "en": "Yelahanka",
                        "te": "యెలాంక",
                        "towns": ["Yelahanka"]
                    }
                }
            },
            "west_godavari": {
                "en": "West Godavari",
                "te": "పశ్చిమ గోదావరి",
                "mandals": {
                    "narsapur": {
                        "en": "Narsapur",
                        "te": "నరసాపురం",
                        "towns": ["Narsapur", "Mandavalli"]
                    },
                    "bhimavaram": {
                        "en": "Bhimavaram",
                        "te": "భీమవరం",
                        "towns": ["Bhimavaram", "Akividu"]
                    },
                    "tadepalligudem": {
                        "en": "Tadepalligudem",
                        "te": "తాడేపల్లిగూడెం",
                        "towns": ["Tadepalligudem", "Nallajerla"]
                    },
                    "elleoru": {
                        "en": "Eluru",
                        "te": "ఏలూరు",
                        "towns": ["Eluru"]
                    }
                }
            },
            "krishna": {
                "en": "Krishna",
                "te": "కృష్ణా",
                "mandals": {
                    "vijayawada": {
                        "en": "Vijayawada",
                        "te": "విజయవాడ",
                        "towns": ["Vijayawada", "Gannavaram"]
                    },
                    "machilipatnam": {
                        "en": "Machilipatnam",
                        "te": "మచిలీపట్నం",
                        "towns": ["Machilipatnam"]
                    },
                    "gudivada": {
                        "en": "Gudivada",
                        "te": "గుడివాడ",
                        "towns": ["Gudivada"]
                    },
                    "nuzvid": {
                        "en": "Nuzvid",
                        "te": "నూజివిడ్",
                        "towns": ["Nuzvid"]
                    }
                }
            },
            "guntur": {
                "en": "Guntur",
                "te": "గుంటూరు",
                "mandals": {
                    "guntur": {
                        "en": "Guntur",
                        "te": "గుంటూరు",
                        "towns": ["Guntur", "Tadikonda"]
                    },
                    "tenali": {
                        "en": "Tenali",
                        "te": "తెనాలి",
                        "towns": ["Tenali"]
                    },
                    "mangalagiri": {
                        "en": "Mangalagiri",
                        "te": "మంగళగిరి",
                        "towns": ["Mangalagiri"]
                    },
                    "sattenapalli": {
                        "en": "Sattenapalli",
                        "te": "సత్తెనపల్లి",
                        "towns": ["Sattenapalli"]
                    }
                }
            },
            "prakasam": {
                "en": "Prakasam",
                "te": "ప్రకాశం",
                "mandals": {
                    "ongole": {
                        "en": "Ongole",
                        "te": "ఒంగోలు",
                        "towns": ["Ongole"]
                    },
                    "chirala": {
                        "en": "Chirala",
                        "te": "చీరాల",
                        "towns": ["Chirala"]
                    },
                    "guntur": {
                        "en": "Bapatla",
                        "te": "బాపట్ల",
                        "towns": ["Bapatla"]
                    }
                }
            },
            "nellore": {
                "en": "Nellore",
                "te": "నెల్లూరు",
                "mandals": {
                    "nellore": {
                        "en": "Nellore",
                        "te": "నెల్లూరు",
                        "towns": ["Nellore"]
                    },
                    "kovuru": {
                        "en": "Kovuru",
                        "te": "కోవూరు",
                        "towns": ["Kovuru"]
                    }
                }
            },
            "chittoor": {
                "en": "Chittoor",
                "te": "చిత్తూరు",
                "mandals": {
                    "chittoor": {
                        "en": "Chittoor",
                        "te": "చిత్తూరు",
                        "towns": ["Chittoor"]
                    },
                    "tirupati": {
                        "en": "Tirupati",
                        "te": "తిరుపతి",
                        "towns": ["Tirupati"]
                    }
                }
            },
            "kadapa": {
                "en": "Kadapa",
                "te": "కడప",
                "mandals": {
                    "kadapa": {
                        "en": "Kadapa",
                        "te": "కడప",
                        "towns": ["Kadapa"]
                    },
                    "proddatur": {
                        "en": "Proddatur",
                        "te": "ప్రొద్దుటూరు",
                        "towns": ["Proddatur"]
                    }
                }
            },
            "anantapur": {
                "en": "Anantapur",
                "te": "అనంతపూర్",
                "mandals": {
                    "anantapur": {
                        "en": "Anantapur",
                        "te": "అనంతపూర్",
                        "towns": ["Anantapur"]
                    },
                    "dharmavaram": {
                        "en": "Dharmavaram",
                        "te": "ధర్మవరం",
                        "towns": ["Dharmavaram"]
                    }
                }
            },
            "kurnool": {
                "en": "Kurnool",
                "te": "కర్నూలు",
                "mandals": {
                    "kurnool": {
                        "en": "Kurnool",
                        "te": "కర్నూలు",
                        "towns": ["Kurnool"]
                    },
                    "nandyal": {
                        "en": "Nandyal",
                        "te": "నంద్యాల",
                        "towns": ["Nandyal"]
                    }
                }
            },
            "srikakulam": {
                "en": "Srikakulam",
                "te": "శ్రీకాకుళం",
                "mandals": {
                    "srikakulam": {
                        "en": "Srikakulam",
                        "te": "శ్రీకాకుళం",
                        "towns": ["Srikakulam"]
                    },
                    "palasa": {
                        "en": "Palasa",
                        "te": "పలాస",
                        "towns": ["Palasa"]
                    }
                }
            },
            "vizianagaram": {
                "en": "Vizianagaram",
                "te": "విజయనగరం",
                "mandals": {
                    "vizianagaram": {
                        "en": "Vizianagaram",
                        "te": "విజయనగరం",
                        "towns": ["Vizianagaram"]
                    }
                }
            },
            "visakhapatnam": {
                "en": "Visakhapatnam",
                "te": "విశాఖపట్నం",
                "mandals": {
                    "visakhapatnam": {
                        "en": "Visakhapatnam",
                        "te": "విశాఖపట్నం",
                        "towns": ["Visakhapatnam"]
                    },
                    "anakapalli": {
                        "en": "Anakapalli",
                        "te": "అనకాపల్లి",
                        "towns": ["Anakapalli"]
                    }
                }
            }
        }
    },
    "telangana": {
        "en": "Telangana",
        "te": "తెలంగాణ",
        "districts": {
            "hyderabad": {
                "en": "Hyderabad",
                "te": "హైదరాబాద్",
                "mandals": {
                    "hyderabad": {
                        "en": "Hyderabad",
                        "te": "హైదరాబాద్",
                        "towns": ["Hyderabad", "Secunderabad"]
                    }
                }
            },
            "ranga_reddy": {
                "en": "Ranga Reddy",
                "te": "రంగారెడ్డి",
                "mandals": {
                    "shamshabad": {
                        "en": "Shamshabad",
                        "te": "షాంషాబాద్",
                        "towns": ["Shamshabad"]
                    },
                    "ibrahimpatnam": {
                        "en": "Ibrahimpatnam",
                        "te": "ఇబ్రహీంపట్నం",
                        "towns": ["Ibrahimpatnam"]
                    }
                }
            },
            "medak": {
                "en": "Medak",
                "te": "మెదక్",
                "mandals": {
                    "medak": {
                        "en": "Medak",
                        "te": "మెదక్",
                        "towns": ["Medak"]
                    }
                }
            },
            "nizamabad": {
                "en": "Nizamabad",
                "te": "నిజామాబాద్",
                "mandals": {
                    "nizamabad": {
                        "en": "Nizamabad",
                        "te": "నిజామాబాద్",
                        "towns": ["Nizamabad"]
                    }
                }
            },
            "warangal": {
                "en": "Warangal",
                "te": "వరంగల్",
                "mandals": {
                    "warangal": {
                        "en": "Warangal",
                        "te": "వరంగల్",
                        "towns": ["Warangal"]
                    }
                }
            },
            "karimnagar": {
                "en": "Karimnagar",
                "te": "కరీంనగర్",
                "mandals": {
                    "karimnagar": {
                        "en": "Karimnagar",
                        "te": "కరీంనగర్",
                        "towns": ["Karimnagar"]
                    }
                }
            },
            "khammam": {
                "en": "Khammam",
                "te": "ఖమ్మం",
                "mandals": {
                    "khammam": {
                        "en": "Khammam",
                        "te": "ఖమ్మం",
                        "towns": ["Khammam"]
                    }
                }
            },
            "nalgonda": {
                "en": "Nalgonda",
                "te": "నల్గొండ",
                "mandals": {
                    "nalgonda": {
                        "en": "Nalgonda",
                        "te": "నల్గొండ",
                        "towns": ["Nalgonda"]
                    },
                    "suryapet": {
                        "en": "Suryapet",
                        "te": "సూర్యాపేట",
                        "towns": ["Suryapet"]
                    }
                }
            }
        }
    },
    "karnataka": {
        "en": "Karnataka",
        "te": "కర్ణాటక",
        "districts": {
            "bangalore": {
                "en": "Bangalore",
                "te": "బెంగళూరు",
                "mandals": {
                    "bangalore": {
                        "en": "Bangalore",
                        "te": "బెంగళూరు",
                        "towns": ["Bangalore"]
                    }
                }
            },
            "mysore": {
                "en": "Mysore",
                "te": "మైసూర్",
                "mandals": {
                    "mysore": {
                        "en": "Mysore",
                        "te": "మైసూర్",
                        "towns": ["Mysore"]
                    }
                }
            }
        }
    },
    "tamil_nadu": {
        "en": "Tamil Nadu",
        "te": "తమిళనాడు",
        "districts": {
            "chennai": {
                "en": "Chennai",
                "te": "చెన్నై",
                "mandals": {
                    "chennai": {
                        "en": "Chennai",
                        "te": "చెన్నై",
                        "towns": ["Chennai"]
                    }
                }
            },
            "coimbatore": {
                "en": "Coimbatore",
                "te": "కోయంబత్తూర్",
                "mandals": {
                    "coimbatore": {
                        "en": "Coimbatore",
                        "te": "కోయంబత్తూర్",
                        "towns": ["Coimbatore"]
                    }
                }
            }
        }
    },
    "maharashtra": {
        "en": "Maharashtra",
        "te": "మహారాష్ట్ర",
        "districts": {
            "pune": {
                "en": "Pune",
                "te": "పుణె",
                "mandals": {
                    "pune": {
                        "en": "Pune",
                        "te": "పుణె",
                        "towns": ["Pune"]
                    }
                }
            },
            "nagpur": {
                "en": "Nagpur",
                "te": "నాగ్‌పూర్",
                "mandals": {
                    "nagpur": {
                        "en": "Nagpur",
                        "te": "నాగ్‌పూర్",
                        "towns": ["Nagpur"]
                    }
                }
            }
        }
    },
    "odisha": {
        "en": "Odisha",
        "te": "ఒడిశా",
        "districts": {
            "cuttack": {
                "en": "Cuttack",
                "te": "కటక్",
                "mandals": {
                    "cuttack": {
                        "en": "Cuttack",
                        "te": "కటక్",
                        "towns": ["Cuttack"]
                    }
                }
            },
            "bhubaneswar": {
                "en": "Bhubaneswar",
                "te": "భువనేశ్వర్",
                "mandals": {
                    "bhubaneswar": {
                        "en": "Bhubaneswar",
                        "te": "భువనేశ్వర్",
                        "towns": ["Bhubaneswar"]
                    }
                }
            }
        }
    }
}

# Agro-climatic zones for location-aware recommendations
AGRO_CLIMATIC_ZONES = {
    "east_godavari": {"zone": "coastal", "rainfall_mm": 1100, "soil_types": ["alluvial", "clay_loam"], "water_availability": "high"},
    "west_godavari": {"zone": "coastal", "rainfall_mm": 1000, "soil_types": ["alluvial", "clay"], "water_availability": "high"},
    "krishna": {"zone": "coastal", "rainfall_mm": 950, "soil_types": ["alluvial", "clay_loam"], "water_availability": "high"},
    "guntur": {"zone": "coastal", "rainfall_mm": 850, "soil_types": ["red", "black"], "water_availability": "medium"},
    "prakasam": {"zone": "coastal_dry", "rainfall_mm": 750, "soil_types": ["red", "sandy_loam"], "water_availability": "medium"},
    "nellore": {"zone": "coastal", "rainfall_mm": 1000, "soil_types": ["alluvial", "red"], "water_availability": "high"},
    "chittoor": {"zone": "rayalaseema", "rainfall_mm": 600, "soil_types": ["red", "sandy_loam"], "water_availability": "low"},
    "kadapa": {"zone": "rayalaseema", "rainfall_mm": 550, "soil_types": ["red", "black"], "water_availability": "low"},
    "anantapur": {"zone": "rayalaseema", "rainfall_mm": 450, "soil_types": ["red_sandy", "sandy_loam"], "water_availability": "low"},
    "kurnool": {"zone": "rayalaseema", "rainfall_mm": 500, "soil_types": ["black", "red"], "water_availability": "low"},
    "srikakulam": {"zone": "coastal", "rainfall_mm": 1050, "soil_types": ["alluvial", "red"], "water_availability": "high"},
    "vizianagaram": {"zone": "coastal", "rainfall_mm": 1000, "soil_types": ["red", "alluvial"], "water_availability": "medium"},
    "visakhapatnam": {"zone": "coastal_hilly", "rainfall_mm": 1100, "soil_types": ["red", "laterite"], "water_availability": "medium"},
    "hyderabad": {"zone": "deccan_plateau", "rainfall_mm": 800, "soil_types": ["black", "red"], "water_availability": "medium"},
    "ranga_reddy": {"zone": "deccan_plateau", "rainfall_mm": 750, "soil_types": ["black", "red"], "water_availability": "medium"},
    "medak": {"zone": "deccan_plateau", "rainfall_mm": 700, "soil_types": ["black", "clay"], "water_availability": "medium"},
    "nizamabad": {"zone": "deccan_plateau", "rainfall_mm": 650, "soil_types": ["black", "clay_loam"], "water_availability": "medium"},
    "warangal": {"zone": "deccan_plateau", "rainfall_mm": 750, "soil_types": ["black", "clay"], "water_availability": "medium"},
    "karimnagar": {"zone": "deccan_plateau", "rainfall_mm": 700, "soil_types": ["black", "clay"], "water_availability": "medium"},
    "khammam": {"zone": "deccan_plateau", "rainfall_mm": 800, "soil_types": ["alluvial", "clay"], "water_availability": "medium"},
    "nalgonda": {"zone": "deccan_plateau", "rainfall_mm": 650, "soil_types": ["black", "red"], "water_availability": "low"},
}


def get_states(lang="en"):
    """Get all states with localized names."""
    return [
        {"id": k, "name": v[lang]}
        for k, v in STATES.items()
    ]


def get_districts(state_id, lang="en"):
    """Get districts for a state."""
    state = STATES.get(state_id, {})
    districts = state.get("districts", {})
    return [
        {"id": k, "name": v[lang]}
        for k, v in districts.items()
    ]


def get_mandals(state_id, district_id, lang="en"):
    """Get mandals for a district."""
    state = STATES.get(state_id, {})
    district = state.get("districts", {}).get(district_id, {})
    mandals = district.get("mandals", {})
    return [
        {"id": k, "name": v[lang]}
        for k, v in mandals.items()
    ]


def get_towns(state_id, district_id, mandal_id, lang="en"):
    """Get towns/villages for a mandal."""
    state = STATES.get(state_id, {})
    district = state.get("districts", {}).get(district_id, {})
    mandal = district.get("mandals", {}).get(mandal_id, {})
    towns = mandal.get("towns", [])
    return [{"id": t.lower().replace(" ", "_"), "name": t} for t in towns]


def get_location_context(state_id, district_id):
    """Get agro-climatic context for a district."""
    return AGRO_CLIMATIC_ZONES.get(district_id, {})
