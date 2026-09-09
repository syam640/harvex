"""
HARVEX Disease Knowledge Base
Structured agricultural reference for tomato disease detection.

Severity rules are based on:
- Disease type (some diseases are inherently more damaging)
- Visual symptoms and progression speed
- Crop impact potential

Treatment recommendations follow IPM (Integrated Pest Management) principles.
Source: ICAR, extension service bulletins, peer-reviewed plant pathology literature.
"""

DISEASE_KNOWLEDGE = {
    "Tomato___Bacterial_spot": {
        "display_name": "Bacterial Spot",
        "severity_base": "Medium",
        "description": "Small, water-soaked spots on leaves, stems, and fruit caused by Xanthomonas bacteria.",
        "progression": "Moderate. Spots enlarge in wet conditions.",
        "crop_impact": "Reduced fruit quality and yield loss of 10-30% if untreated.",
        "actions": {
            "immediate": [
                "Remove and destroy affected leaves immediately",
                "Avoid working with wet plants",
                "Improve air circulation between plants",
            ],
            "cultural": [
                "Use drip irrigation instead of overhead watering",
                "Rotate crops - avoid tomato/pepper for 2-3 years",
                "Use disease-free seed and transplants",
                "Mulch to prevent soil splash onto leaves",
            ],
            "prevention": [
                "Apply copper-based bactericide as preventive spray",
                "Use resistant varieties where available",
                "Sanitize tools between plants",
            ],
            "biological": [
                "Bacillus subtilis sprays can reduce bacterial spread",
            ],
            "chemical": "Copper hydroxide or copper sulfate sprays. Apply every 7-10 days during wet weather. Consult local agricultural extension for approved products.",
            "expert_note": "If more than 30% of foliage is affected, consult an agricultural extension officer for intensive management."
        }
    },
    "Tomato___Early_blight": {
        "display_name": "Early Blight",
        "severity_base": "Medium",
        "description": "Dark concentric ring spots (target-like) on older leaves caused by Alternaria solani.",
        "progression": "Moderate to fast in warm, humid conditions. Moves upward from lower leaves.",
        "crop_impact": "Can cause 20-40% yield loss if unmanaged. Defoliation reduces fruit set.",
        "actions": {
            "immediate": [
                "Remove affected lower leaves",
                "Apply fungicide at first sign of symptoms",
                "Reduce leaf wetness duration",
            ],
            "cultural": [
                "Stake plants to improve air circulation",
                "Mulch to prevent soil splash (spores overwinter in soil)",
                "Water at base of plants, avoid wetting foliage",
                "Remove crop debris after harvest",
            ],
            "prevention": [
                "Apply chlorothalonil or mancozeb preventively every 7-14 days",
                "Use crop rotation (3-year minimum)",
                "Plant resistant varieties when available",
            ],
            "biological": [
                "Bacillus amyloliquefaciens shows efficacy against Alternaria",
            ],
            "chemical": "Chlorothalonil, mancozeb, or azoxystrobin. Begin applications at first symptoms and repeat every 7-10 days. Follow pre-harvest intervals on labels.",
            "expert_note": "If disease appears before fruit set, yield impact will be highest. Prioritize immediate fungicide application."
        }
    },
    "Tomato___Late_blight": {
        "display_name": "Late Blight",
        "severity_base": "High",
        "description": "Large, irregular water-soaked lesions with white fuzzy growth. Caused by Phytophthora infestans.",
        "progression": "Very fast. Can destroy entire crop in 7-10 days under cool, wet conditions.",
        "crop_impact": "Potentially 100% crop loss. Most destructive tomato disease.",
        "actions": {
            "immediate": [
                "Remove and destroy ALL affected plants immediately (do not compost)",
                "Apply fungicide urgently to surrounding healthy plants",
                "Improve drainage around plants",
            ],
            "cultural": [
                "Avoid overhead irrigation completely",
                "Increase plant spacing for air circulation",
                "Do not work in fields when foliage is wet",
                "Remove volunteer tomato and potato plants nearby",
            ],
            "prevention": [
                "Use resistant varieties (most important measure)",
                "Apply preventive fungicide during wet seasons",
                "Monitor weather forecasts - high risk during cool, wet periods",
            ],
            "biological": [
                "Bacillus subtilis may provide some suppression",
            ],
            "chemical": "Metalaxyl + mancozeb (Ridomil Gold) or fosetyl-aluminum. Apply immediately and repeat every 5-7 days. This is an emergency situation.",
            "expert_note": "Late blight is an epidemic disease. Report to local agricultural authorities if detected. Complete crop loss is possible."
        }
    },
    "Tomato___Leaf_Mold": {
        "display_name": "Leaf Mold",
        "severity_base": "Low",
        "description": "Yellow patches on upper leaf surface with olive-green to brown fuzzy mold underneath. Caused by Passalora fulva.",
        "progression": "Slow to moderate. Primarily affects greenhouse tomatoes.",
        "crop_impact": "Usually 10-15% yield loss. Rarely kills plants but reduces photosynthesis.",
        "actions": {
            "immediate": [
                "Remove heavily affected leaves",
                "Improve ventilation to reduce humidity",
            ],
            "cultural": [
                "Reduce humidity below 85% (critical for this disease)",
                "Increase spacing between plants",
                "Prune lower leaves to improve air flow",
            ],
            "prevention": [
                "Maintain humidity below 80%",
                "Use resistant varieties",
                "Ensure good greenhouse ventilation",
            ],
            "biological": [
                "No major biological controls registered for this pathogen",
            ],
            "chemical": "Mancozeb or chlorothalonil sprays. Usually cultural control (humidity management) is sufficient.",
            "expert_note": "Primarily a greenhouse disease. In open field, humidity management is usually sufficient."
        }
    },
    "Tomato___Septoria_leaf_spot": {
        "display_name": "Septoria Leaf Spot",
        "severity_base": "Medium",
        "description": "Small, circular spots with dark borders and gray centers on lower leaves. Caused by Septoria lycopersici.",
        "progression": "Moderate. Starts on lower leaves and moves upward.",
        "crop_impact": "Can cause significant defoliation and 15-30% yield loss.",
        "actions": {
            "immediate": [
                "Remove affected lower leaves",
                "Apply fungicide to prevent spread to upper canopy",
            ],
            "cultural": [
                "Mulch to prevent rain splash",
                "Rotate crops (3-year minimum)",
                "Remove crop debris after harvest",
                "Avoid overhead watering",
            ],
            "prevention": [
                "Use disease-free seed",
                "Apply preventive fungicide during wet weather",
                "Maintain adequate plant nutrition (avoid excess nitrogen)",
            ],
            "biological": [
                "Bacillus-based products may provide some suppression",
            ],
            "chemical": "Chlorothalonil or copper-based fungicides. Apply every 7-10 days during wet conditions.",
            "expert_note": "Often occurs alongside Early Blight. If both are present, use a broad-spectrum fungicide."
        }
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "display_name": "Spider Mites",
        "severity_base": "Medium",
        "description": "Tiny arachnids causing stippling, yellowing, and webbing on leaves. Two-spotted spider mite (Tetranychus urticae).",
        "progression": "Fast in hot, dry conditions. Population explodes above 30°C.",
        "crop_impact": "Severe infestations cause leaf drop and 20-50% yield loss.",
        "actions": {
            "immediate": [
                "Spray plants with strong water jet to dislodge mites",
                "Remove heavily infested leaves",
                "Apply miticide if population is high",
            ],
            "cultural": [
                "Maintain adequate irrigation (mites thrive in dry conditions)",
                "Avoid dusty conditions around plants",
                "Use reflective mulches to deter mites",
            ],
            "prevention": [
                "Monitor undersides of leaves regularly",
                "Maintain plant vigor through proper nutrition",
                "Avoid broad-spectrum insecticides that kill natural predators",
            ],
            "biological": [
                "Release predatory mites (Phytoseiulus persimilis)",
                "Encourage natural predators: ladybugs, lacewings",
                "Beauveria bassiana-based products",
            ],
            "chemical": "Abamectin, spiromesifen, or fenpyroximate. Rotate classes to prevent resistance. Avoid spraying during bloom to protect pollinators.",
            "expert_note": "Spider mites are not insects - many insecticides are ineffective. Use specific miticides."
        }
    },
    "Tomato___Target_Spot": {
        "display_name": "Target Spot",
        "severity_base": "Medium",
        "description": "Brown spots with concentric rings on leaves, stems, and fruit. Caused by Corynespora cassiicola.",
        "progression": "Moderate. Worsened by warm, humid conditions.",
        "crop_impact": "Can cause 15-35% yield loss through defoliation and fruit rot.",
        "actions": {
            "immediate": [
                "Remove affected leaves and fallen fruit",
                "Apply fungicide to prevent spread",
            ],
            "cultural": [
                "Improve air circulation",
                "Avoid overhead irrigation",
                "Remove crop debris",
                "Practice crop rotation",
            ],
            "prevention": [
                "Use resistant varieties",
                "Apply preventive fungicide during high humidity",
            ],
            "biological": [
                "Trichoderma-based biofungicides may help",
            ],
            "chemical": "Azoxystrobin, difenoconazole, or propiconazole. Apply every 7-10 days during favorable conditions.",
            "expert_note": "Target Spot can be confused with Early Blight. Proper diagnosis is important for correct treatment."
        }
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "display_name": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "severity_base": "High",
        "description": "Upward curling of leaves, yellowing, stunted growth. Transmitted by whiteflies (Bemisia tabaci).",
        "progression": "No cure once infected. Spread by whitefly vector.",
        "crop_impact": "Severe stunting and 50-100% yield loss in young plants.",
        "actions": {
            "immediate": [
                "Remove and destroy infected plants (cannot be cured)",
                "Control whitefly population immediately",
            ],
            "cultural": [
                "Use virus-resistant tomato varieties (most important)",
                "Install yellow sticky traps for whitefly monitoring",
                "Use reflective mulches to repel whiteflies",
                "Plant barrier crops (maize) around tomato fields",
            ],
            "prevention": [
                "Use resistant/tolerant varieties (e.g., Ty-1, Ty-2 genes)",
                "Control whitefly vectors early in the season",
                "Remove weeds that harbor virus and whiteflies",
                "Use insect-proof netting in nurseries",
            ],
            "biological": [
                "Encourage natural enemies of whiteflies: Encarsia formosa, Chrysoperla",
            ],
            "chemical": "Imidacloprid, thiamethoxam, or flupyradifurone for whitefly control. Note: neonicotinoids have resistance issues in some regions.",
            "expert_note": "No cure exists for TYLCV. Prevention through resistant varieties and whitefly management is the only strategy."
        }
    },
    "Tomato___Tomato_mosaic_virus": {
        "display_name": "Tomato Mosaic Virus (ToMV)",
        "severity_base": "Medium",
        "description": "Mottled light and dark green on leaves, sometimes with leaf distortion. Highly stable virus.",
        "progression": "Systemic infection. No cure. Spread by mechanical contact.",
        "crop_impact": "10-30% yield reduction. Fruit may show uneven ripening.",
        "actions": {
            "immediate": [
                "Remove and destroy infected plants",
                "Disinfect hands and tools with 10% bleach solution",
            ],
            "cultural": [
                "Use resistant varieties (most effective control)",
                "Wash hands before handling plants",
                "Do not use tobacco products near plants (related virus)",
                "Sanitize stakes, cages, and tools",
            ],
            "prevention": [
                "Use certified disease-free seed",
                "Treat seed in 10% bleach for 10 minutes if seed-borne",
                "Use resistant varieties (Tm-2 gene)",
                "Avoid touching healthy plants after handling infected ones",
            ],
            "biological": [
                "No biological controls for viral diseases",
            ],
            "chemical": "No chemical treatment for viruses. Focus on vector control and hygiene.",
            "expert_note": "ToMV is extremely stable and can survive on surfaces for months. Hygiene is the most critical control measure."
        }
    },
    "Tomato___healthy": {
        "display_name": "Healthy",
        "severity_base": "Healthy",
        "description": "No disease detected. Plant appears healthy.",
        "progression": "N/A",
        "crop_impact": "N/A",
        "actions": {
            "immediate": [],
            "cultural": [
                "Continue regular monitoring",
                "Maintain balanced nutrition",
                "Ensure adequate irrigation",
            ],
            "prevention": [
                "Continue regular scouting for pests and diseases",
                "Maintain good cultural practices",
                "Keep records of observations",
            ],
            "biological": [],
            "chemical": "No treatment needed.",
            "expert_note": "Regular monitoring is key to early detection. Scout plants at least twice a week."
        }
    },
}

CONFIDENCE_THRESHOLD = 0.45

def get_disease_info(disease_class: str):
    return DISEASE_KNOWLEDGE.get(disease_class)

def determine_severity(disease_class: str, confidence: float) -> str:
    if not disease_class or not isinstance(disease_class, str):
        return "Unknown"

    if "healthy" in disease_class.lower():
        return "Healthy"

    info = DISEASE_KNOWLEDGE.get(disease_class)
    if not info:
        return "Unknown"

    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        return "Unknown"

    if conf != conf or conf < 0 or conf > 1:
        return "Unknown"

    base = info.get("severity_base", "Medium")

    if conf < CONFIDENCE_THRESHOLD:
        return "Low"

    if base == "High":
        return "High"
    elif base == "Medium":
        if conf >= 0.8:
            return "High"
        elif conf >= 0.6:
            return "Medium"
        else:
            return "Low"
    elif base == "Low":
        if conf >= 0.85:
            return "Medium"
        else:
            return "Low"

    return "Medium"

def get_confidence_quality(confidence: float, predicted_class: str) -> dict:
    if "healthy" in predicted_class.lower():
        if confidence >= 0.6:
            return {"reliable": True, "message": "Plant appears healthy"}
        else:
            return {"reliable": False, "message": "Unable to confirm plant health. Please upload a clearer image."}

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "reliable": False,
            "message": "Confidence too low for reliable diagnosis. Please upload a clearer leaf image showing symptoms."
        }
    elif confidence < 0.55:
        return {
            "reliable": True,
            "message": "Low confidence result. Consider uploading another image for confirmation. Consult an expert for definitive diagnosis."
        }
    else:
        return {
            "reliable": True,
            "message": "Result appears reliable."
        }
