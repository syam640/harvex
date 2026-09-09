import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { useFarm } from '../contexts/FarmContext';
import { intelligentCropAPI, farmsAPI, parseApiError } from '../services/api';
import PageHeader from '../components/PageHeader';
import {
  Sprout, Loader2, AlertCircle, CheckCircle2, Sun,
  MapPin, ChevronDown, ChevronUp, Info,
  AlertTriangle, Droplets
} from 'lucide-react';

interface CropCandidate {
  crop_id: string;
  name_en: string;
  name_te: string;
  category: string;
  suitability_score: number;
  component_scores: Record<string, number>;
  limiting_factors: string[];
  reasoning: Record<string, string> | null;
  conflicts: string[] | null;
  recommendation_notes: string[] | null;
  water_requirement: string;
  risk_factors: string[];
  data_sources: { name: string; type: string; status: string }[];
}

interface RecommendationResult {
  status: string;
  data_quality: {
    overall: string;
    weather: string;
    soil: string;
    npk: string;
    water: string;
    irrigation: string;
    missing_data: string[];
  };
  recommendations: CropCandidate[];
  total_evaluated: number;
  eligible_count: number;
  ai_used: boolean;
  ai_provider: string | null;
  ai_model: string | null;
  processing_time_ms: number | null;
}

const WATER_OPTIONS = [
  { value: 'very_limited', label_en: 'Very Limited', label_te: 'చాలా తక్కువ' },
  { value: 'limited', label_en: 'Limited', label_te: 'తక్కువ' },
  { value: 'moderate', label_en: 'Moderate', label_te: 'మధ్యస్థం' },
  { value: 'good', label_en: 'Good', label_te: 'మంచిది' },
  { value: 'abundant', label_en: 'Abundant', label_te: 'సమృద్ధిగా' },
  { value: 'rainfed_only', label_en: 'Rainfed Only', label_te: 'వర్షాధారమే' },
];

const IRRIGATION_OPTIONS = [
  { value: 'drip', label_en: 'Drip', label_te: 'డ్రిప్' },
  { value: 'sprinkler', label_en: 'Sprinkler', label_te: 'స్ప్రింక్లర్' },
  { value: 'flood', label_en: 'Flood', label_te: 'వరద పద్ధతి' },
  { value: 'furrow', label_en: 'Furrow', label_te: 'కాలువ పద్ధతి' },
  { value: 'rainfed', label_en: 'Rainfed', label_te: 'వర్షాధార' },
  { value: 'other', label_en: 'Other', label_te: 'ఇతర' },
];

const SEASON_OPTIONS = [
  { value: 'kharif', label_en: 'Kharif (Jun-Oct)', label_te: 'ఖరీఫ్ (జూన్–అక్టోబర్)' },
  { value: 'rabi', label_en: 'Rabi (Nov-Mar)', label_te: 'రబీ (నవంబర్–మార్చి)' },
  { value: 'summer', label_en: 'Summer (Apr-May)', label_te: 'వేసవి (ఏప్రిల్–మే)' },
];

const getCropEmoji = (cropId: string) => {
  const c = cropId.toLowerCase();
  if (c.includes('tomato')) return '🍅';
  if (c.includes('rice')) return '🌾';
  if (c.includes('maize')) return '🌽';
  if (c.includes('cotton')) return '🧶';
  if (c.includes('chilli') || c.includes('chili')) return '🌶️';
  if (c.includes('onion')) return '🧅';
  if (c.includes('potato')) return '🥔';
  if (c.includes('brinjal') || c.includes('eggplant')) return '🍆';
  if (c.includes('mango')) return '🥭';
  if (c.includes('banana')) return '🍌';
  if (c.includes('groundnut') || c.includes('peanut')) return '🥜';
  if (c.includes('wheat')) return '🌾';
  if (c.includes('sugarcane')) return '🎋';
  if (c.includes('coconut')) return '🥥';
  if (c.includes('soybean')) return '🫘';
  if (c.includes('sunflower')) return '🌻';
  if (c.includes('sesame')) return '🫘';
  if (c.includes('mustard')) return '🌻';
  if (c.includes('chickpea')) return '🫘';
  if (c.includes('pigeon')) return '🫘';
  if (c.includes('green_gram') || c.includes('moong')) return '🫘';
  if (c.includes('black_gram') || c.includes('urad')) return '🫘';
  if (c.includes('lentil')) return '🫘';
  if (c.includes('okra')) return '🫛';
  if (c.includes('cabbage')) return '🥬';
  if (c.includes('papaya')) return '🍈';
  if (c.includes('guava')) return '🍓';
  if (c.includes('pomegranate')) return '🍓';
  if (c.includes('turmeric')) return '🥜';
  if (c.includes('ginger')) return '🥜';
  if (c.includes('jute')) return '🌿';
  if (c.includes('sweet_potato')) return '🥔';
  if (c.includes('coffee')) return '☕';
  if (c.includes('pearl_millet') || c.includes('finger_millet')) return '🌾';
  if (c.includes('sorghum')) return '🌾';
  return '🌱';
};

const getScoreColor = (score: number) => {
  if (score >= 75) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  if (score >= 50) return 'text-amber-700 bg-amber-50 border-amber-200';
  return 'text-red-700 bg-red-50 border-red-200';
};

const getScoreLabel = (score: number, lang: string) => {
  if (lang === 'te') {
    if (score >= 85) return 'అద్భుతం';
    if (score >= 70) return 'మంచిది';
    if (score >= 50) return 'మధ్యస్థం';
    return 'తక్కువ';
  }
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Moderate';
  return 'Low';
};

export default function IntelligentCropRecommendation() {
  const navigate = useNavigate();
  const { t, language } = useLanguage();
  const { refreshFarm, ensureFarmAndField } = useFarm();

  const [season, setSeason] = useState('kharif');
  const [waterAvail, setWaterAvail] = useState('moderate');
  const [irrigation, setIrrigation] = useState('rainfed');
  const [location, setLocation] = useState<{ lat: number | null; lon: number | null; name: string }>({
    lat: null, lon: null, name: '',
  });
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [error, setError] = useState('');
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const [selectedCrop, setSelectedCrop] = useState<string | null>(null);
  const [analysisStages, setAnalysisStages] = useState<{ key: string; labelEn: string; labelTe: string; status: 'pending' | 'active' | 'done' }[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (loading) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(prev => prev + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [loading]);

  const persistLocationToFarm = useCallback(async (lat: number, lon: number) => {
    try {
      await ensureFarmAndField();
      await farmsAPI.updateFarmLocation(lat, lon);
      await refreshFarm();
    } catch {
      // Non-critical: weather may show "Set location" but crop AI still works
    }
  }, [refreshFarm, ensureFarmAndField]);

  const requestGPS = useCallback(() => {
    setGpsLoading(true);
    setGpsError('');
    if (!navigator.geolocation) {
      setGpsError(language === 'te' ? 'GPS అందుబాటులో లేదు. కోఆర్డినేట్లు మాన్యువల్‌గా నమోదు చేయండి.' : 'GPS not available. Enter coordinates manually.');
      setGpsLoading(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setLocation({ lat, lon, name: `${lat.toFixed(4)}, ${lon.toFixed(4)}` });
        setGpsLoading(false);
        persistLocationToFarm(lat, lon);
      },
      () => {
        setGpsError(language === 'te' ? 'స్థాన అనుమతి నిరాకరించబడింది. కోఆర్డినేట్లు మాన్యువల్‌గా నమోదు చేయండి.' : 'Location access denied. Enter coordinates manually.');
        setGpsLoading(false);
      },
      { timeout: 10000, maximumAge: 300000 }
    );
  }, [language, persistLocationToFarm]);

  const handleManualLocation = (lat: string, lon: string) => {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (!isNaN(latNum) && !isNaN(lonNum)) {
      setLocation({ lat: latNum, lon: lonNum, name: `${latNum.toFixed(4)}, ${lonNum.toFixed(4)}` });
      persistLocationToFarm(latNum, lonNum);
    }
  };

  const handleGetRecommendation = async () => {
    if (!location.lat || !location.lon) {
      setError(language === 'te' ? 'దయచేసి మీ పొలం స్థానాన్ని అందించండి (GPS లేదా మాన్యువల్ కోఆర్డినేట్లు)' : 'Please provide your farm location (GPS or manual coordinates)');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    setAnalysisStages([
      { key: 'location', labelEn: 'Location received', labelTe: 'స్థానం స్వీకరించబడింది', status: 'done' },
      { key: 'conditions', labelEn: 'Farm conditions loaded', labelTe: 'పొలం పరిస్థితులు లోడ్ అయ్యాయి', status: 'active' },
      { key: 'weather', labelEn: 'Weather checked', labelTe: 'వాతావరణం తనిఖీ చేయబడింది', status: 'pending' },
      { key: 'soil', labelEn: 'Soil information checked', labelTe: 'నేల సమాచారం తనిఖీ చేయబడింది', status: 'pending' },
      { key: 'ai', labelEn: 'AI is researching suitable crops', labelTe: 'AI అనుకూల పంటలను పరిశోధిస్తోంది', status: 'pending' },
      { key: 'ranking', labelEn: 'Ranking suitable crops', labelTe: 'అనుకూల పంటలను ర్యాంక్ చేస్తోంది', status: 'pending' },
    ]);

    const updateStage = (key: string, status: 'done' | 'active') => {
      setAnalysisStages(prev => prev.map(s => s.key === key ? { ...s, status } : s));
    };

    try {
      updateStage('conditions', 'done');
      updateStage('weather', 'active');

      const res = await intelligentCropAPI.recommend({
        latitude: location.lat,
        longitude: location.lon,
        location_name: location.name,
        location_source: gpsError ? 'manual' : 'gps',
        season,
        water_availability: waterAvail,
        irrigation_method: irrigation,
      });

      updateStage('weather', 'done');
      updateStage('soil', 'done');
      updateStage('ai', 'done');
      updateStage('ranking', 'done');

      if (res.data.status === 'success') {
        setResult(res.data);
      } else if (res.data.status === 'insufficient_data') {
        setError(language === 'te' ? 'స్థిరమైన పంట సిఫార్సు కోసం తగినంత డేటా లేదు.' : 'Insufficient data for a reliable crop recommendation. Please check your location and try again.');
      } else {
        setError(language === 'te' ? 'సిఫార్సు పూర్తి చేయడం సాధ్యం కాలేదు' : 'Recommendation could not be completed');
      }
    } catch (err: unknown) {
      const msg = parseApiError(err);
      if (msg.includes('timeout') || msg.includes('504') || msg.includes('503')) {
        setError(language === 'te' ? '⚠️ విశ్లేషణ పూర్తవడానికి ఎక్కువ సమయం పట్టింది. మీ నెట్‌వర్క్ లేదా AI సేవ నెమ్మదిగా ఉండవచ్చు.' : '⚠️ The analysis took too long to complete. Your network or AI service may be slow.');
      } else {
        setError(msg);
      }
      setAnalysisStages(prev => prev.map(s => s.status === 'active' ? { ...s, status: 'done' } : s));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCrop = (cropId: string) => {
    setSelectedCrop(cropId);
  };

  const handleConfirmCrop = async () => {
    if (!selectedCrop) return;
    setConfirming(true);
    setError('');
    try {
      const { field: currentField } = await ensureFarmAndField();
      const cropName = result?.recommendations.find(r => r.crop_id === selectedCrop)?.name_en || selectedCrop;
      const now = new Date().toISOString();
      const cycleRes = await farmsAPI.createCropCycle({
        field_id: currentField.id,
        crop_name: cropName,
        planting_date: now,
      });
      if (cycleRes.data?.id) {
        await refreshFarm();
        navigate('/dashboard');
      } else {
        setError(language === 'te' ? 'పంట సైకిల్ సృష్టించడం సాధ్యం కాలేదు' : 'Failed to create crop cycle');
      }
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title={t('smartCropRecommendation') || 'Smart Crop Recommendation'}
        subtitle={t('harvexAnalysis') || 'HARVEX analyzes your farm conditions and recommends the best crops for your land.'}
        icon={<Sprout className="h-6 w-6" />}
      />

      {/* Location Section */}
      <div className="card">
        <h3 className="font-bold text-charcoal-900 mb-4 flex items-center gap-2">
          <MapPin className="h-5 w-5 text-primary-600" />
          {t('farmLocation') || 'Farm Location'}
        </h3>

        {!location.lat ? (
          <div className="space-y-4">
            <button
              onClick={requestGPS}
              disabled={gpsLoading}
              className="w-full btn-primary py-3 flex items-center justify-center gap-2"
            >
              {gpsLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <MapPin className="h-5 w-5" />
              )}
              {gpsLoading
                ? (language === 'te' ? 'స్థానం పొందుతోంది...' : 'Getting location...')
                : (t('useGps') || 'Use My GPS Location')}
            </button>

            {gpsError && (
              <p className="text-sm text-amber-700 bg-amber-50 p-3 rounded-lg">{gpsError}</p>
            )}

            <div className="text-center text-sm text-charcoal-500">{language === 'te' ? 'లేదా మాన్యువల్‌గా నమోదు చేయండి' : '-- or enter manually --'}</div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">{t('latitude') || 'Latitude'}</label>
                <input
                  type="number"
                  step="0.0001"
                  placeholder={language === 'te' ? 'ఉదా: 16.5062' : 'e.g. 16.5062'}
                  className="input-field"
                  onChange={(e) => {
                    const lonInput = document.getElementById('manual-lon') as HTMLInputElement;
                    handleManualLocation(e.target.value, lonInput?.value || '');
                  }}
                />
              </div>
              <div>
                <label className="label">{t('longitude') || 'Longitude'}</label>
                <input
                  id="manual-lon"
                  type="number"
                  step="0.0001"
                  placeholder={language === 'te' ? 'ఉదా: 80.6480' : 'e.g. 80.6480'}
                  className="input-field"
                  onChange={(e) => {
                    const latInput = document.querySelector('input[placeholder*="16.5"]') as HTMLInputElement;
                    handleManualLocation(latInput?.value || '', e.target.value);
                  }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between bg-emerald-50 p-3 rounded-lg">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              <span className="font-medium text-emerald-800">{location.name}</span>
            </div>
            <button
              onClick={() => setLocation({ lat: null, lon: null, name: '' })}
              className="text-sm text-emerald-700 underline"
            >
              {language === 'te' ? 'మార్చండి' : 'Change'}
            </button>
          </div>
        )}
      </div>

      {/* Farm Conditions */}
      <div className="card">
        <h3 className="font-bold text-charcoal-900 mb-4 flex items-center gap-2">
          <Sun className="h-5 w-5 text-primary-600" />
          {t('farmConditions') || 'Farm Conditions'}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">{language === 'te' ? 'పంట కాలం' : 'Season'}</label>
            <select value={season} onChange={(e) => setSeason(e.target.value)} className="input-field">
              {SEASON_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{language === 'te' ? o.label_te : o.label_en}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">{t('waterAvailability') || 'Water Availability'}</label>
            <select value={waterAvail} onChange={(e) => setWaterAvail(e.target.value)} className="input-field">
              {WATER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{language === 'te' ? o.label_te : o.label_en}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">{t('irrigationMethod') || 'Irrigation Method'}</label>
            <select value={irrigation} onChange={(e) => setIrrigation(e.target.value)} className="input-field">
              {IRRIGATION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{language === 'te' ? o.label_te : o.label_en}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleGetRecommendation}
        disabled={loading || !location.lat}
        className="w-full btn-primary btn-pill text-lg py-4 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            {t('analyzingFarm') || 'Analyzing farm conditions...'}
          </>
        ) : (
          <>
            <Sprout className="h-5 w-5" />
            {t('getCropRecButton') || 'Get Crop Recommendations'}
          </>
        )}
      </button>

      {/* Staged Progress with honest timing */}
      {loading && analysisStages.length > 0 && (
        <div className="card text-center py-6">
          <h3 className="text-lg font-bold text-charcoal-900 mb-2">
            {t('analyzingFarm') || 'HARVEX is analyzing your farm'}
          </h3>
          <p className="text-sm text-charcoal-500 mb-2">
            {t('pleaseWait') || 'Please wait while HARVEX compares your farm conditions with suitable crops.'}
          </p>
          {elapsed < 60 ? (
            <p className="text-charcoal-400 text-xs italic mb-4">
              {language === 'te'
                ? '🌱 HARVEX ఆలోచిస్తోంది... మీ పొల పరిస్థితులను అనుకూలమైన పంటలతో AI పోల్చుతున్నందుకు కొంచెం సమయం పడుతుంది. సాధారణంగా 5 నిమిషాల్లోపు పూర్తవుతుంది. 😄🌾'
                : '🌱 HARVEX is thinking... This can take a little while while AI compares your farm conditions with suitable crops. Usually less than 5 minutes. 😄🌾'}
            </p>
          ) : (
            <p className="text-amber-600 text-xs italic mb-4">
              {language === 'te'
                ? '🐢 ఊహించిన దానికంటే కొంచెం ఎక్కువ సమయం పడుతోంది. మీ పొల విశ్లేషణ ఇంకా కొనసాగుతోంది. మీ నెట్‌వర్క్ కనెక్షన్‌ను ఒకసారి పరిశీలించి HARVEX‌కు ఇంకొంచెం సమయం ఇవ్వండి. 🌱'
                : '🐢 This is taking longer than expected. Your farm analysis is still running. Please check your network connection and give HARVEX a little more time. 🌱'}
            </p>
          )}
          <div className="max-w-sm mx-auto space-y-2 text-left">
            {analysisStages.map(stage => (
              <div key={stage.key} className="flex items-center gap-3">
                {stage.status === 'done' && <CheckCircle2 className="h-4 w-4 text-success shrink-0" />}
                {stage.status === 'active' && <Loader2 className="h-4 w-4 text-primary-500 animate-spin shrink-0" />}
                {stage.status === 'pending' && <div className="w-4 h-4 rounded-full border-2 border-charcoal-300 shrink-0" />}
                <span className={`text-sm ${
                  stage.status === 'done' ? 'text-charcoal-700' :
                  stage.status === 'active' ? 'text-primary-600 font-medium' : 'text-charcoal-400'
                }`}>
                  {language === 'te' ? stage.labelTe : stage.labelEn}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card bg-danger-light border-danger/20 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-danger-dark mt-0.5" />
          <div className="flex-1">
            <p className="text-danger-dark">{error}</p>
            <button onClick={() => { setError(''); setResult(null); }} className="btn-outline mt-2 text-sm">
              {t('tryAgain') || 'Try Again'}
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {result && result.recommendations.length > 0 && (
        <div className="space-y-6 animate-slide-up">
          {/* Data Quality Banner */}
          <div className="card bg-gradient-to-r from-primary-50 to-emerald-50 border-primary-200">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-primary-600 mt-0.5" />
              <div className="text-sm">
                <p className="font-bold text-primary-800 mb-1">{language === 'te' ? 'ఉపయోగించిన డేటా మూలాలు' : 'Data Sources Used'}</p>
                <div className="flex flex-wrap gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    result.data_quality.weather === 'available' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {language === 'te' ? 'వాతావరణం' : 'Weather'}: {result.data_quality.weather}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    result.data_quality.soil !== 'unavailable' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {language === 'te' ? 'నేల' : 'Soil'}: {result.data_quality.soil}
                  </span>
                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-sky-100 text-sky-800">
                    {language === 'te' ? 'మూల్యాంకనం' : 'Evaluated'}: {result.total_evaluated} {language === 'te' ? 'పంటలు' : 'crops'}
                  </span>
                  {result.ai_used && (
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-violet-100 text-violet-800">
                      AI: {result.ai_provider}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Top 15 Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-charcoal-900">
              {language === 'te' ? 'మీ పొలం కోసం టాప్ పంటలు' : 'Top Crops for Your Farm'}
            </h2>
            <span className="text-sm text-charcoal-500">
              {result.recommendations.length} {language === 'te' ? 'పంటలు సిఫార్సు చేయబడ్డాయి' : 'crops recommended'}
            </span>
          </div>

          {/* Crop Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {result.recommendations.map((crop, i) => {
              const isExpanded = expandedCard === crop.crop_id;
              const isSelected = selectedCrop === crop.crop_id;
              const displayName = language === 'te' ? crop.name_te : crop.name_en;
              const secondaryName = language === 'te' ? crop.name_en : crop.name_te;
              return (
                <div
                  key={crop.crop_id}
                  className={`card-hover cursor-pointer transition-all ${
                    isSelected ? 'ring-2 ring-primary-500 bg-primary-50' : ''
                  } ${i === 0 ? 'md:col-span-2 lg:col-span-2 bg-gradient-to-br from-primary-50 to-emerald-50 border-primary-200' : ''}`}
                  onClick={() => handleSelectCrop(crop.crop_id)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className={i === 0 ? 'text-6xl' : 'text-4xl'}>{getCropEmoji(crop.crop_id)}</span>
                      <div>
                        <h3 className={`font-bold ${i === 0 ? 'text-2xl' : 'text-lg'} text-charcoal-900`}>
                          {displayName}
                        </h3>
                        <p className="text-charcoal-500 text-sm">{secondaryName}</p>
                        <span className="text-xs bg-charcoal-100 text-charcoal-600 px-2 py-0.5 rounded-full">
                          {crop.category}
                        </span>
                      </div>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-sm font-bold border ${getScoreColor(crop.suitability_score)}`}>
                      {crop.suitability_score.toFixed(0)}/100
                    </div>
                  </div>

                  <div className="mb-3">
                    <span className="text-sm font-medium text-charcoal-700">
                      {language === 'te' ? 'పొలం అనుకూలత' : 'Farm Suitability'}: {getScoreLabel(crop.suitability_score, language)}
                    </span>
                  </div>

                  {/* Component Scores */}
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    {Object.entries(crop.component_scores).slice(0, 4).map(([key, val]) => (
                      <div key={key} className="text-center">
                        <div className="text-xs text-charcoal-500 capitalize">{key}</div>
                        <div className={`text-sm font-bold ${val >= 70 ? 'text-emerald-600' : val >= 40 ? 'text-amber-600' : 'text-red-600'}`}>
                          {val.toFixed(0)}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Water & Risk */}
                  <div className="flex items-center gap-4 text-xs text-charcoal-600 mb-3">
                    <div className="flex items-center gap-1">
                      <Droplets className="h-3 w-3 text-sky-500" />
                      {language === 'te' ? 'నీరు' : 'Water'}: {crop.water_requirement}
                    </div>
                    {crop.risk_factors.length > 0 && (
                      <div className="flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3 text-amber-500" />
                        {language === 'te' ? 'ప్రమాదం' : 'Risk'}: {crop.risk_factors[0]}
                      </div>
                    )}
                  </div>

                  {/* Limiting Factors */}
                  {crop.limiting_factors.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-amber-700 mb-1">{language === 'te' ? 'గమనించండి:' : 'Watch:'}</p>
                      <div className="flex flex-wrap gap-1">
                        {crop.limiting_factors.map((lf, j) => (
                          <span key={j} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">
                            {lf}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Expand/Collapse */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedCard(isExpanded ? null : crop.crop_id);
                    }}
                    className="text-xs text-primary-600 flex items-center gap-1 hover:underline"
                  >
                    {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    {isExpanded ? (language === 'te' ? 'తక్కువ వివరాలు' : 'Less detail') : (language === 'te' ? 'మరిన్ని వివరాలు' : 'More detail')}
                  </button>

                  {/* Expanded Details */}
                  {isExpanded && crop.reasoning && (
                    <div className="mt-3 pt-3 border-t border-charcoal-100 space-y-2 text-xs text-charcoal-700">
                      {Object.entries(crop.reasoning).map(([key, val]) => (
                        val && typeof val === 'string' && (
                          <div key={key}>
                            <span className="font-medium capitalize">{key}:</span> {val}
                          </div>
                        )
                      ))}
                      {crop.conflicts && crop.conflicts.length > 0 && (
                        <div className="bg-amber-50 p-2 rounded">
                          <p className="font-medium text-amber-800">{language === 'te' ? 'సంఘర్షణలు:' : 'Conflicts:'}</p>
                          {crop.conflicts.map((c, j) => <p key={j} className="text-amber-700">{c}</p>)}
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1 mt-2">
                        {crop.data_sources.map((ds, j) => (
                          <span key={j} className="text-xs bg-charcoal-100 text-charcoal-600 px-2 py-0.5 rounded-full">
                            {ds.name} ({ds.status})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Selected Crop Confirmation */}
          {selectedCrop && (
            <div className="card bg-primary-50 border-primary-200 sticky bottom-4 z-10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-4xl">{getCropEmoji(selectedCrop)}</span>
                  <div>
                    <p className="text-sm text-primary-600 font-medium">{language === 'te' ? 'ఎంచుకున్న పంట' : 'Selected Crop'}</p>
                    <p className="font-bold text-primary-900 text-lg">
                      {result.recommendations.find(r => r.crop_id === selectedCrop)?.name_en}
                      <span className="text-primary-600 ml-2 text-sm">
                        {result.recommendations.find(r => r.crop_id === selectedCrop)?.name_te}
                      </span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleConfirmCrop}
                  disabled={confirming}
                  className="btn-success btn-pill px-8"
                >
                  {confirming ? (
                    <Loader2 className="h-5 w-5 inline mr-2 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-5 w-5 inline mr-2" />
                  )}
                  {language === 'te' ? 'సాగు ప్రారంభించండి' : 'Start Farming'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* No Results */}
      {result && result.recommendations.length === 0 && (
        <div className="card bg-amber-50 border-amber-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div>
              <p className="font-bold text-amber-800">{language === 'te' ? 'అనుకూల పంటలు కనుగొనబడలేదు' : 'No suitable crops found'}</p>
              <p className="text-sm text-amber-700 mt-1">
                {language === 'te'
                  ? '10 కంటే తక్కువ పంటలు ప్రస్తుత అనుకూలత ప్రమాణాలను కలిగి ఉన్నాయి. మీ నీటి లభ్యత లేదా నీటిపారుదల విధానాన్ని సర్దుబాటు చేయండి.'
                  : 'Fewer than 10 crops meet the current suitability criteria. Try adjusting your water availability or irrigation method.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
