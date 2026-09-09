"""All AI prompt templates for HARVEX — optimized for speed."""

SYSTEM_PROMPT_BASE = (
    "You are HARVEX, an agricultural decision-support platform for Indian farmers.\n"
    "Use ONLY the data provided. NEVER invent measurements, yields, prices, or dosages.\n"
    "If information is missing, say it is unavailable.\n"
    "Preserve all numbers, units, Rs., temperatures, crop/disease names.\n"
)


def system_prompt(language: str = "en") -> str:
    prompt = SYSTEM_PROMPT_BASE
    if language == "te":
        prompt += (
            "\nIMPORTANT: Answer in Telugu. "
            "Keep numbers, units, currency, crop/disease names in English/numeric form."
        )
    return prompt


def crop_recommendation_prompt(context: dict) -> str:
    loc = context.get('location', 'India')
    temp = context.get('temperature', 'unknown')
    hum = context.get('humidity', 'unknown')
    rain = context.get('rainfall', 'unknown')
    soil = context.get('soil_type', 'unknown')
    crop = context.get('crop_name', 'none')
    area = context.get('area_acres', 'unknown')
    cond = context.get('weather_condition', 'unknown')

    return f"""Indian farm in {loc}. Soil: {soil}. Area: {area} acres. Current crop: {crop}. Temp: {temp} deg C. Humidity: {hum}%. Rainfall: {rain}mm. Weather: {cond}.

Recommend best 3 crops. Output ONLY valid JSON:
{{"recommended_crop":"Rice","suitability":"High","reasons":["Warm weather suits rice","Rainfall is adequate","Loamy soil is good for rice"],"favorable_factors":["Temperature","Rainfall"],"limiting_factors":["No soil test available"],"water_requirement":"high","major_risks":["Flood risk"],"uncertainties":["Market price unknown"],"alternatives":[{{"crop":"Maize","suitability":"Medium","reasons":["Good temperature range"],"limiting_factors":["Needs irrigation"]}},{{"crop":"Groundnut","suitability":"Medium","reasons":["Suitable for loamy soil"],"limiting_factors":["Needs moderate water"]}}]}}"""


def disease_analysis_prompt(crop: str, context: dict = None) -> str:
    ctx = ""
    if context:
        if context.get("location"):
            ctx += f" Location: {context['location']}."
        if context.get("growth_stage"):
            ctx += f" Growth stage: {context['growth_stage']}."
        if context.get("description"):
            ctx += f" User notes: {context['description']}."
        if context.get("previous_disease"):
            ctx += f" Previous observation: {context['previous_disease']} (severity: {context.get('previous_severity','unknown')})."

    return f"""Analyze this plant image for health assessment.

CRITICAL: Return ONLY a valid JSON object. No markdown. No explanation outside JSON.

Required JSON schema:
{{
  "crop": "string or null",
  "health_status": "Healthy | Diseased | Unable to determine",
  "disease_name": "string or null",
  "severity": "None | Mild | Moderate | Severe | Unknown",
  "confidence": "number between 0 and 1 or null",
  "visual_evidence": ["array of strings describing visible symptoms"],
  "explanation": "string explaining your assessment",
  "needs_follow_up": true,
  "needs_better_image": false
}}

Rules for this image analysis:
- Identify the disease ONLY from what you actually SEE in this image.
- Do NOT assume any disease based on the crop name alone.
- If the image is blurry, too small, or does not show a plant, set health_status to "Unable to determine".
- If the plant looks healthy, set disease_name to null, severity to "None", confidence to 0.9+.
- If you cannot identify the crop, still analyze the image, set crop to "{crop}" with a note.
- Never fabricate a disease. If unsure, set health_status to "Unable to determine".
- Use null where information cannot be established.
- For follow-up scans: compare with previous observation if provided.
{ctx}

Return ONLY the JSON object. No other text."""


def disease_analysis_retry_prompt(crop: str, context: dict = None) -> str:
    """Retry prompt when first attempt fails to return valid JSON."""
    ctx = ""
    if context:
        if context.get("location"):
            ctx += f" Location: {context['location']}."
        if context.get("growth_stage"):
            ctx += f" Growth stage: {context['growth_stage']}."
        if context.get("description"):
            ctx += f" User notes: {context['description']}."

    return f"""CRITICAL: Your previous response was not valid JSON. You MUST return ONLY a valid JSON object.

Analyze this plant image for health assessment.

Required JSON schema:
{{
  "crop": "string or null",
  "health_status": "Healthy | Diseased | Unable to determine",
  "disease_name": "string or null",
  "severity": "None | Mild | Moderate | Severe | Unknown",
  "confidence": "number between 0 and 1 or null",
  "visual_evidence": ["array of strings describing visible symptoms"],
  "explanation": "string explaining your assessment",
  "needs_follow_up": true,
  "needs_better_image": false
}}

Rules:
- Identify disease ONLY from what you SEE in the image.
- If the image is unclear, set health_status to "Unable to determine".
- If healthy, set disease_name to null, severity to "None".
- Use null where information cannot be established.
{ctx}

Return ONLY the JSON object. No markdown. No explanation. No other text."""


def treatment_prompt(crop: str, disease: str, severity: str, weather: dict = None) -> str:
    w = f"Temp: {weather.get('temperature','?')} deg C, Humidity: {weather.get('humidity','?')}%, Rain: {weather.get('rainfall','?')}mm" if weather else "Weather unknown"
    return f"""Treatment guidance for {crop} with {disease} (severity: {severity}). Weather: {w}.

This is AI visual decision support, NOT a laboratory diagnosis.
Treatment should be conservative when confidence is low.

Output ONLY valid JSON:
{{"immediate_actions":["<action 1>","<action 2>"],"cultural_or_organic_actions":["<action 1>"],"chemical_options":["<general guidance only - consult local agricultural extension>"],"precautions":["<precaution 1>"],"follow_up_days":3,"reassessment_reason":"<why follow-up is needed>","safety_note":"Follow product label and local agricultural guidance for any chemical application. Do not apply pesticides without local expert confirmation.","uncertainty_note":"<any uncertainty about the diagnosis that affects treatment>"}}

Rules:
- NEVER fabricate pesticide names, concentrations, application rates, or waiting periods.
- NEVER claim a treatment will definitely cure the disease.
- Use "Consult local agricultural extension" for chemical recommendations.
- If severity is mild or confidence is low, emphasize monitoring over aggressive treatment.
- Cultural and organic actions should be safe for any crop.
- Include safety precautions for any field activity.
- If the diagnosis is uncertain, say so and recommend re-examination."""


def risk_analysis_prompt(crop: str, crop_stage: str, weather: dict, disease_info: dict = None) -> str:
    w = f"Temp: {weather.get('temperature','?')} deg C, Humidity: {weather.get('humidity','?')}%, Rain: {weather.get('rainfall','?')}mm, Wind: {weather.get('wind_speed','?')}km/h, Condition: {weather.get('condition','?')}" if weather else "Weather unknown"
    d = f"Disease: {disease_info.get('disease','?')}, Severity: {disease_info.get('severity','?')}" if disease_info else "No disease data"
    return f"""Risk analysis for {crop} ({crop_stage}). Weather: {w}. Disease: {d}.
Output ONLY valid JSON:
{{"disease_fungal_risk":{{"level":"MEDIUM","drivers":["High humidity","Recent rainfall"],"evidence":["Humidity above 70%"],"uncertainty":"No disease model available"}},"heat_stress_risk":{{"level":"LOW","drivers":["Moderate temperature"],"evidence":["Temp within safe range"],"uncertainty":""}},"heavy_rain_risk":{{"level":"MEDIUM","drivers":["Rainfall expected"],"evidence":["Current rainfall significant"],"uncertainty":"Forecast uncertain"}},"water_stress_risk":{{"level":"LOW","drivers":["Adequate rainfall"],"evidence":["Recent rain"],"uncertainty":"Soil moisture not measured"}},"wind_risk":{{"level":"LOW","drivers":["Low wind speed"],"evidence":[],"uncertainty":""}},"overall_risk":"MEDIUM","key_concerns":["Fungal disease risk elevated"],"urgent_actions":["Monitor for leaf spots","Ensure drainage"]}}"""


def irrigation_prompt(crop: str, crop_stage: str, weather: dict, soil_type: str = None) -> str:
    w = f"Temp: {weather.get('temperature','?')} deg C, Humidity: {weather.get('humidity','?')}%, Rain: {weather.get('rainfall','?')}mm, Condition: {weather.get('condition','?')}" if weather else "Weather unknown"
    s = f"Soil: {soil_type}" if soil_type else "Soil type: Unknown"
    return f"""Should farmer irrigate {crop} ({crop_stage})? {s}. Weather: {w}.
Output ONLY valid JSON:
{{"recommendation":"DELAY","reasons":["Rainfall expected in forecast","Current humidity is adequate","Recent rain provides sufficient moisture"],"water_deficit_assessment":"No water deficit detected based on recent rainfall","soil_moisture_note":"Actual soil moisture data is unavailable","confidence":"medium"}}"""


def financial_analysis_prompt(expenses: list, harvests: list, crop: str) -> str:
    exp_lines = []
    for e in (expenses or []):
        amt = f"{e.get('amount',0):,.0f}"
        exp_lines.append(f"- {e.get('category','?')}: Rs.{amt}")
    exp = "\n".join(exp_lines) if exp_lines else "No expenses"
    harv_lines = []
    for h in (harvests or []):
        sp = f"{h.get('selling_price',0)}"
        rev = f"{h.get('revenue',0):,.0f}"
        harv_lines.append(f"- {h.get('quantity',0)} {h.get('unit','kg')} @ Rs.{sp} = Rs.{rev}")
    harv = "\n".join(harv_lines) if harv_lines else "No harvests"
    return f"""Financial analysis for {crop}. Expenses: {exp}. Harvests: {harv}.
Output ONLY valid JSON:
{{"total_cost":0,"total_revenue":0,"net_profit":0,"profit_margin":"N/A","largest_expense_category":"Seeds","financial_health":"moderate","key_insights":["Track expenses by category","Record harvest selling prices"],"recommendations":["Add more expense details","Record harvest quantities"]}}"""


def what_if_prompt(current_decision: dict, scenario_changes: dict, context: dict) -> str:
    return f"""What-if analysis. Current: {current_decision}. Scenario: {scenario_changes}. Farm: {context.get('crop_name','?')}, {context.get('location','?')}.
Output ONLY valid JSON:
{{"scenario_name":"What-If","impact_summary":"Scenario changes evaluated","score_change":"Score may change based on conditions","effects":[{{"factor":"water","impact":"Irrigation needs change","direction":"positive"}}],"recommendations":["Monitor conditions","Adjust plan accordingly"],"uncertainties":["Weather forecast uncertain","Soil conditions unknown"]}}"""


def farm_insight_prompt(context: dict, expenses_summary: dict = None, harvest_summary: dict = None) -> str:
    crop = context.get('crop_name', 'Unknown')
    loc = context.get('location', 'Unknown')
    temp = context.get('temperature', '?')
    exp_total = expenses_summary.get('total', 0) if expenses_summary else 0
    rev_total = harvest_summary.get('total_revenue', 0) if harvest_summary else 0
    exp_str = f"{exp_total:,.0f}"
    rev_str = f"{rev_total:,.0f}"
    return f"""Farm insights for {crop} at {loc}. Temp: {temp} deg C. Expenses: Rs.{exp_str}. Revenue: Rs.{rev_str}.
Output ONLY valid JSON:
{{"insights":[{{"category":"crop","title":"Active crop cycle","description":"{crop} is currently growing","priority":"medium","source":"farm data"}},{{"category":"financial","title":"Financial tracking","description":"Total expenses Rs.{exp_str}, Revenue Rs.{rev_str}","priority":"medium","source":"farm data"}}],"summary":"Farm is active with {crop}. Continue monitoring conditions."}}"""


def assistant_prompt(context: dict, question: str) -> str:
    ctx = "\n".join([f"- {k}: {v}" for k, v in context.items() if v is not None and v != ""]) if context else "No farm data"
    return f"""Farm Context:\n{ctx}\n\nFarmer's Question: {question}\n\nAnswer based on the farm context. Explain WHY when recommending actions."""


def location_crop_recommendation_prompt(
    state_id: str,
    district_id: str,
    mandal_id: str = None,
    season: str = None,
    soil_type: str = None,
    location_context: dict = None,
) -> str:
    state = state_id.replace("_", " ").title()
    district = district_id.replace("_", " ").title()
    mandal = mandal_id.replace("_", " ").title() if mandal_id else "Not specified"
    zone = location_context.get("zone", "unknown") if location_context else "unknown"
    rainfall = location_context.get("rainfall_mm", "unknown") if location_context else "unknown"
    soils = ", ".join(location_context.get("soil_types", [])) if location_context else "unknown"
    water = location_context.get("water_availability", "unknown") if location_context else "unknown"

    season_info = f"Season: {season}" if season else "Season: Current"
    soil_info = f"Soil: {soil_type}" if soil_type else f"Common soils: {soils}"

    return f"""Indian farm in {state}, {district}, {mandal}. Zone: {zone}. Rainfall: {rainfall}mm/year. Water availability: {water}. {soil_info}. {season_info}.

Recommend best 3 crops for this location. Consider local climate, soil, water availability, and market demand.

Output ONLY valid JSON:
{{"recommended_crop":"Rice","suitability":"High","reasons":["Coastal climate suits rice","High water availability","Alluvial soil ideal"],"favorable_factors":["Rainfall","Water availability","Soil type"],"limiting_factors":[],"water_requirement":"high","major_risks":["Flood risk in monsoon"],"uncertainties":["Market price fluctuation"],"alternatives":[{{"crop":"Maize","suitability":"Medium","reasons":["Good for this zone"],"limiting_factors":["Needs irrigation"]}},{{"crop":"Groundnut","suitability":"Medium","reasons":["Suitable soil type"],"limiting_factors":["Moderate water needs"]}}],"location_recommendations":["Best time to plant: June-July","Local market prices should be checked"],"seasonal_note":"Current season is favorable for Kharif crops"}}"""


def crop_research_prompt(context_json: str, candidate_ids: list) -> str:
    """Structured AI crop research prompt. Receives structured facts + crop catalog IDs.
    Returns JSON with reasoning for each candidate."""
    crop_list = ", ".join(candidate_ids)
    return f"""You are analyzing farm conditions for crop suitability. You have structured farm context and a list of candidate crops.

Analyze each candidate crop against the farm context. For each crop, provide reasoning about soil, climate, water, irrigation, season, location, and risk compatibility.

You MUST ONLY use crop IDs from this list: {crop_list}
Do NOT invent new crop IDs.

Farm context:
{context_json}

CRITICAL: You MUST return ONLY valid JSON. No markdown. No prose outside JSON.

ABSOLUTE RULES — YOU MUST NOT:
- Invent soil pH, nitrogen, phosphorus, potassium values that are not in the farm context
- Invent temperature, rainfall, humidity values that are not in the farm context
- Create coordinates, soil type, or water availability that are not in the farm context
- If data is marked "unavailable", state it is unavailable — do NOT fabricate a value

You may ONLY reason from the supplied facts and canonical crop metadata.
If information is unavailable, explicitly state that it is unavailable in your reasoning.

Required JSON schema:
{{
  "recommendation_status": "success",
  "data_quality": {{
    "overall": "good|partial|minimal",
    "missing_data": ["list of missing data fields"]
  }},
  "candidates": [
    {{
      "crop_id": "rice",
      "reasoning": {{
        "soil": "explanation of soil compatibility using ONLY provided soil data",
        "climate": "explanation of climate compatibility using ONLY provided weather data",
        "water": "explanation of water compatibility using ONLY provided water availability",
        "irrigation": "explanation of irrigation compatibility using ONLY provided irrigation method",
        "season": "explanation of season compatibility",
        "location": "explanation of location compatibility",
        "risk": "explanation of risk factors using ONLY provided data"
      }},
      "conflicts": ["list of any conflicts detected"],
      "recommendation_notes": ["any additional notes"]
    }}
  ]
}}

Rules:
- ONLY analyze crops from the provided candidate list.
- Use the farm context data as-is. Do NOT fabricate new measurements.
- If soil data is unavailable, say so in reasoning. Do NOT invent soil values.
- If weather data is unavailable, say so in reasoning. Do NOT invent weather values.
- Identify conflicts between farm conditions and crop requirements.
- Return reasoning for ALL eligible candidates (not just top ones).
- Every crop_id in your response must be from the provided candidate list."""


def crop_research_retry_prompt(context_json: str, candidate_ids: list) -> str:
    """Retry prompt when first AI attempt fails."""
    crop_list = ", ".join(candidate_ids)
    return f"""CRITICAL: Your previous response was not valid JSON. You MUST return ONLY a valid JSON object.

Analyze farm conditions for crop suitability.

Candidate crops: {crop_list}

Farm context:
{context_json}

ABSOLUTE RULES — YOU MUST NOT:
- Invent soil pH, nitrogen, phosphorus, potassium values that are not in the farm context
- Invent temperature, rainfall, humidity values that are not in the farm context
- Create coordinates, soil type, or water availability that are not in the farm context
- If data is marked "unavailable", state it is unavailable — do NOT fabricate a value

Return ONLY valid JSON matching this schema:
{{
  "recommendation_status": "success",
  "data_quality": {{"overall": "partial", "missing_data": []}},
  "candidates": [
    {{
      "crop_id": "rice",
      "reasoning": {{"soil": "...", "climate": "...", "water": "...", "irrigation": "...", "season": "...", "location": "...", "risk": "..."}},
      "conflicts": [],
      "recommendation_notes": []
    }}
  ]
}}

Rules:
- ONLY use crop IDs from: {crop_list}
- Do NOT fabricate measurements.
- Return ONLY the JSON object. No markdown. No explanation."""


def crop_research_fallback_prompt(context_json: str, candidate_ids: list) -> str:
    """Fallback model prompt — same strictness, used when primary model fails entirely."""
    crop_list = ", ".join(candidate_ids)
    return f"""You are a crop suitability analyst. Analyze farm conditions and provide structured reasoning.

Candidate crops: {crop_list}

Farm context:
{context_json}

CRITICAL: You MUST return ONLY valid JSON. No markdown. No prose outside JSON.

ABSOLUTE RULES — YOU MUST NOT:
- Invent soil pH, nitrogen, phosphorus, potassium values that are not in the farm context
- Invent temperature, rainfall, humidity values that are not in the farm context
- Create coordinates, soil type, or water availability that are not in the farm context
- If data is marked "unavailable", state it is unavailable — do NOT fabricate a value

You may ONLY reason from the supplied facts and canonical crop metadata.
If information is unavailable, explicitly state that it is unavailable in your reasoning.

Required JSON schema:
{{
  "recommendation_status": "success",
  "data_quality": {{"overall": "partial", "missing_data": []}},
  "candidates": [
    {{
      "crop_id": "rice",
      "reasoning": {{
        "soil": "using ONLY provided soil data",
        "climate": "using ONLY provided weather data",
        "water": "using ONLY provided water availability",
        "irrigation": "using ONLY provided irrigation method",
        "season": "season compatibility",
        "location": "location compatibility",
        "risk": "risk factors using ONLY provided data"
      }},
      "conflicts": [],
      "recommendation_notes": []
    }}
  ]
}}

Rules:
- ONLY use crop IDs from: {crop_list}
- Do NOT fabricate measurements.
- Return ONLY the JSON object. No markdown. No explanation."""
