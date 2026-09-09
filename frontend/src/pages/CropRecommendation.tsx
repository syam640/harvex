import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { aiAPI, parseApiError } from '../services/api';
import { Sprout, Loader2, AlertCircle, CheckCircle2, Leaf, Droplets, Sun } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import LocationSelector from '../components/LocationSelector';

interface CropRecommendation {
  recommended_crop: string;
  suitability: string;
  reasons: string[];
  favorable_factors: string[];
  limiting_factors: string[];
  water_requirement: string;
  major_risks: string[];
  alternatives: {
    crop: string;
    suitability: string;
    reasons: string[];
  }[];
  location_recommendations?: string[];
  seasonal_note?: string;
}

const getCropEmoji = (crop: string) => {
  const c = crop.toLowerCase();
  if (c.includes('tomato') || c.includes('tom')) return '🍅';
  if (c.includes('rice') || c.includes('paddy')) return '🌾';
  if (c.includes('maize') || c.includes('corn')) return '🌽';
  if (c.includes('cotton')) return '🤍';
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
  return '🌱';
};

export default function CropRecommendation() {
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [location, setLocation] = useState({
    state: '',
    district: '',
    mandal: '',
    town: '',
  });
  const [season, setSeason] = useState('');
  const [soilType, setSoilType] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CropRecommendation | null>(null);
  const [error, setError] = useState('');

  const handleGetRecommendation = async () => {
    if (!location.state || !location.district) {
      setError('Please select your location (State and District)');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await aiAPI.getLocationCropRecommendation({
        state_id: location.state,
        district_id: location.district,
        mandal_id: location.mandal || undefined,
        season: season || undefined,
        soil_type: soilType || undefined,
      });

      if (res.data.available && res.data.data) {
        setResult(res.data.data);
      } else {
        setError(res.data.message || 'AI recommendation unavailable');
      }
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleStartCrop = () => {
    navigate('/dashboard');
  };

  const getSuitabilityColor = (suitability: string) => {
    switch (suitability?.toLowerCase()) {
      case 'high': return 'badge-success';
      case 'medium': return 'badge-warning';
      case 'low': return 'badge-danger';
      default: return 'badge-info';
    }
  };

  return (
    <div className="page-container">
      <PageHeader 
        title="Smart Crop Recommendation" 
        subtitle="Tell HARVEX where you farm. We'll recommend the best crop for your location."
        icon={<Sprout className="h-6 w-6" />}
      />

      {/* Location Selection */}
      <LocationSelector
        onLocationChange={setLocation}
        showTown={false}
      />

      {/* Additional Options */}
      <div className="card">
        <h3 className="font-bold text-charcoal-900 mb-4">Additional Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">{t('season')}</label>
            <select
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              className="input-field"
            >
              <option value="">-- Select Season --</option>
              <option value="kharif">{t('kharif')} (Jun-Oct)</option>
              <option value="rabi">{t('rabi')} (Nov-Mar)</option>
              <option value="zaid">{t('zaid')} (Mar-Jun)</option>
            </select>
          </div>
          <div>
            <label className="label">{t('soilType')}</label>
            <select
              value={soilType}
              onChange={(e) => setSoilType(e.target.value)}
              className="input-field"
            >
              <option value="">-- Select Soil Type --</option>
              <option value="alluvial">Alluvial</option>
              <option value="black">Black</option>
              <option value="red">Red</option>
              <option value="laterite">Laterite</option>
              <option value="sandy">Sandy</option>
              <option value="clay">Clay</option>
              <option value="loamy">Loamy</option>
            </select>
          </div>
        </div>
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleGetRecommendation}
        disabled={loading || !location.state || !location.district}
        className="w-full btn-primary btn-pill text-lg py-4 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            HARVEX is analyzing your farm context...
          </>
        ) : (
          <>
            <Sprout className="h-5 w-5" />
            Analyze My Farm
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="card bg-danger-light border-danger/20 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-danger-dark mt-0.5" />
          <p className="text-danger-dark">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* Primary Recommendation */}
          <div className="card bg-gradient-to-br from-primary-50 to-primary-100 border-primary-200">
            <div className="text-center mb-6">
              <span className="text-7xl block mb-4">{getCropEmoji(result.recommended_crop)}</span>
              <p className="text-sm text-charcoal-500 font-medium">Recommended For You</p>
              <h2 className="text-4xl font-extrabold text-charcoal-900 mt-1">
                {result.recommended_crop}
              </h2>
              <span className={`badge ${getSuitabilityColor(result.suitability)} mt-2 text-lg px-4 py-1`}>
                {result.suitability} Suitability
              </span>
            </div>

            {/* Reasons */}
            {result.reasons && result.reasons.length > 0 && (
              <div className="bg-white/50 rounded-2xl p-4 mb-4">
                <p className="font-bold text-charcoal-800 mb-3 flex items-center gap-2">
                  <Leaf className="h-5 w-5 text-primary-600" />
                  Why this crop is recommended
                </p>
                <ul className="space-y-2">
                  {result.reasons.map((reason, i) => (
                    <li key={i} className="flex items-start gap-2 text-charcoal-700">
                      <CheckCircle2 className="h-5 w-5 text-primary-500 mt-0.5 flex-shrink-0" />
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Factors */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              {result.favorable_factors && result.favorable_factors.length > 0 && (
                <div className="bg-success-light/50 rounded-2xl p-3">
                  <p className="text-sm font-bold text-success-dark mb-2">Favorable Factors</p>
                  <div className="flex flex-wrap gap-1">
                    {result.favorable_factors.map((f, i) => (
                      <span key={i} className="text-xs bg-white/70 text-success-dark px-2 py-1 rounded-lg">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {result.limiting_factors && result.limiting_factors.length > 0 && (
                <div className="bg-warning-light/50 rounded-2xl p-3">
                  <p className="text-sm font-bold text-warning-dark mb-2">Limiting Factors</p>
                  <div className="flex flex-wrap gap-1">
                    {result.limiting_factors.map((f, i) => (
                      <span key={i} className="text-xs bg-white/70 text-warning-dark px-2 py-1 rounded-lg">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Water & Risks */}
            <div className="flex items-center justify-center gap-6 text-sm text-charcoal-600">
              {result.water_requirement && (
                <div className="flex items-center gap-1">
                  <Droplets className="h-4 w-4 text-sky-500" />
                  Water: <strong>{result.water_requirement}</strong>
                </div>
              )}
              {result.major_risks && result.major_risks.length > 0 && (
                <div className="flex items-center gap-1">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  Risk: <strong>{result.major_risks[0]}</strong>
                </div>
              )}
            </div>

            {/* Start Farm Button */}
            <div className="mt-6 text-center">
              <button onClick={handleStartCrop} className="btn-success btn-pill text-lg px-12">
                <CheckCircle2 className="h-5 w-5 inline mr-2" />
                START FARM
              </button>
            </div>
          </div>

          {/* Seasonal Note */}
          {result.seasonal_note && (
            <div className="card bg-sky-50 border-sky-200">
              <div className="flex items-start gap-2">
                <Sun className="h-5 w-5 text-sky-600 mt-0.5" />
                <p className="text-sm text-sky-800">{result.seasonal_note}</p>
              </div>
            </div>
          )}

          {/* Alternatives */}
          {result.alternatives && result.alternatives.length > 0 && (
            <div>
              <h3 className="text-xl font-bold text-charcoal-900 mb-4">Alternative Crops</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {result.alternatives.map((alt, i) => (
                  <div key={i} className="card-hover">
                    <div className="flex items-center gap-3">
                      <span className="text-4xl">{getCropEmoji(alt.crop)}</span>
                      <div className="flex-1">
                        <h4 className="font-bold text-charcoal-900">{alt.crop}</h4>
                        <span className={`badge ${getSuitabilityColor(alt.suitability)}`}>
                          {alt.suitability}
                        </span>
                      </div>
                    </div>
                    {alt.reasons && alt.reasons.length > 0 && (
                      <p className="text-sm text-charcoal-600 mt-2">{alt.reasons[0]}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
