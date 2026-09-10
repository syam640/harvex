import { useState, useRef, useEffect } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { useLanguage } from '../contexts/LanguageContext';
import { diseaseAPI, parseApiError } from '../services/api';
import { Upload, Camera, AlertTriangle, Bug, Loader2, CheckCircle, Info, Sprout, Search } from 'lucide-react';
import PageHeader from '../components/PageHeader';

interface DiseaseResult {
  supported: boolean;
  crop?: string;
  health_status?: string;
  predicted_disease?: string;
  confidence?: number | null;
  severity?: string;
  model_version?: string;
  provider?: string;
  model_name?: string;
  visual_evidence?: string[];
  explanation?: string;
  needs_follow_up?: boolean;
  needs_better_image?: boolean;
  message?: string;
  display_name?: string;
  top_predictions?: { disease: string; confidence: number }[];
  quality_check?: { quality: string; provider?: string; error?: string };
  treatment?: {
    immediate_actions?: string[];
    cultural_or_organic_actions?: string[];
    chemical_options?: string[];
    precautions?: string[];
    follow_up_days?: number;
    reassessment_reason?: string;
    safety_note?: string;
    uncertainty_note?: string;
  } | null;
  description?: string;
}

interface AnalysisStage {
  key: string;
  labelEn: string;
  labelTe: string;
  status: 'pending' | 'active' | 'done' | 'error';
}

const CROP_OPTIONS = [
  { value: 'tomato', labelEn: 'Tomato', labelTe: 'టమాటా', emoji: '🍅' },
  { value: 'maize', labelEn: 'Maize', labelTe: 'మొక్కజొన్న', emoji: '🌽' },
  { value: 'rice', labelEn: 'Rice', labelTe: 'వరి', emoji: '🌾' },
  { value: 'cotton', labelEn: 'Cotton', labelTe: 'పత్తి', emoji: '🤍' },
  { value: 'chilli', labelEn: 'Chilli', labelTe: 'మిరప', emoji: '🌶️' },
  { value: 'onion', labelEn: 'Onion', labelTe: 'ఉల్లిపాయ', emoji: '🧅' },
  { value: 'potato', labelEn: 'Potato', labelTe: 'బంగాళాదుంప', emoji: '🥔' },
  { value: 'brinjal', labelEn: 'Brinjal', labelTe: 'వంకాయ', emoji: '🍆' },
  { value: 'wheat', labelEn: 'Wheat', labelTe: 'గోధుమ', emoji: '🌾' },
  { value: 'groundnut', labelEn: 'Groundnut', labelTe: 'వేరుశనగ', emoji: '🥜' },
  { value: 'mango', labelEn: 'Mango', labelTe: 'మామిడి', emoji: '🥭' },
  { value: 'banana', labelEn: 'Banana', labelTe: 'అరటి', emoji: '🍌' },
  { value: 'grapes', labelEn: 'Grapes', labelTe: 'ద్రాక్ష', emoji: '🍇' },
  { value: 'coconut', labelEn: 'Coconut', labelTe: 'కొబ్బరి', emoji: '🥥' },
  { value: 'sugarcane', labelEn: 'Sugarcane', labelTe: 'చెరకు', emoji: '🎋' },
];

type CropMode = null | 'present' | 'another';

export default function Disease() {
  const { t, language } = useLanguage();
  const { cropCycle, setDiseaseResult } = useFarm();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [cropMode, setCropMode] = useState<CropMode>(null);
  const [modelLoading, setModelLoading] = useState(false);
  const [stages, setStages] = useState<AnalysisStage[]>([]);
  const [result, setResult] = useState<DiseaseResult | null>(null);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedCrop, setSelectedCrop] = useState<string>('');
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const activeCropName = cropCycle?.crop_name?.toLowerCase() || '';

  useEffect(() => {
    if (modelLoading) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(prev => prev + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [modelLoading]);

  const updateStage = (key: string, status: AnalysisStage['status']) => {
    setStages(prev => prev.map(s => s.key === key ? { ...s, status } : s));
  };

  const handleModeSelect = (mode: 'present' | 'another') => {
    setCropMode(mode);
    setResult(null);
    setError('');
    setPreview(null);
    if (mode === 'present' && activeCropName) {
      setSelectedCrop(activeCropName);
    } else {
      setSelectedCrop('');
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!selectedCrop) {
      setError(language === 'te' ? 'దయచేసి ఆకు చిత్రాన్ని అప్‌లోడ్ చేయడానికి ముందు మీ పంటను ఎంచుకోండి.' : 'Please select your crop before uploading a leaf image.');
      return;
    }

    if (!file.type.match(/image\/(jpeg|png|webp)/)) {
      setError(language === 'te' ? 'దయచేసి JPEG, PNG, లేదా WEBP చిత్రాన్ని అప్‌లోడ్ చేయండి' : 'Please upload a JPEG, PNG, or WEBP image');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError(language === 'te' ? 'ఫైల్ పరిమాణం 10MB కంటే తక్కువగా ఉండాలి' : 'File size must be less than 10MB');
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => setPreview(ev.target?.result as string);
    reader.readAsDataURL(file);

    setError('');
    setResult(null);
    setModelLoading(true);
    setStages([
      { key: 'upload', labelEn: 'Image uploaded', labelTe: 'చిత్రం అప్‌లోడ్ చేయబడింది', status: 'done' },
      { key: 'quality', labelEn: 'Image quality checked', labelTe: 'చిత్ర నాణ్యత తనిఖీ చేయబడింది', status: 'active' },
      { key: 'examining', labelEn: 'AI is examining visible symptoms', labelTe: 'AI కనిపించే లక్షణాలను పరిశీలిస్తోంది', status: 'pending' },
      { key: 'identifying', labelEn: 'Identifying possible crop condition', labelTe: 'సాధ్యమైన పంట పరిస్థితిని గుర్తిస్తోంది', status: 'pending' },
      { key: 'explaining', labelEn: 'Preparing explanation', labelTe: 'వివరణ సిద్ధం చేస్తోంది', status: 'pending' },
    ]);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('crop_name', selectedCrop);

      updateStage('quality', 'done');
      updateStage('examining', 'active');

      const res = await diseaseAPI.scan(formData);

      updateStage('examining', 'done');
      updateStage('identifying', 'done');
      updateStage('explaining', 'done');

      setResult(res.data);
      if (res.data.supported) {
        setDiseaseResult(res.data);
      }
    } catch (err: unknown) {
      setError(parseApiError(err));
      setStages(prev => prev.map(s => s.status === 'active' ? { ...s, status: 'error' } : s));
    } finally {
      setModelLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && fileInputRef.current) {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInputRef.current.files = dataTransfer.files;
      handleFileSelect({ target: { files: [file] } } as any);
    }
  };

  const handleReset = () => {
    setCropMode(null);
    setSelectedCrop('');
    setResult(null);
    setError('');
    setPreview(null);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'severe': return 'badge-danger';
      case 'moderate': return 'badge-warning';
      case 'mild': return 'badge-info';
      case 'none': return 'badge-success';
      default: return 'badge-success';
    }
  };

  const getCropEmoji = (crop: string) => {
    return CROP_OPTIONS.find(c => c.value === crop)?.emoji || '🌱';
  };

  const isHealthy = result?.health_status === 'healthy' || result?.predicted_disease === 'None';
  const isDiseased = result?.health_status === 'diseased' && !isHealthy;
  const isUnableToDetermine = result?.predicted_disease === 'Unable to determine' || result?.health_status === 'unable_to_determine';

  return (
    <div className="page-container">
      <PageHeader
        title={t('diseaseDetection') || 'Crop Health Check'}
        subtitle={t('uploadLeaf') || 'Upload a clear leaf image and let HARVEX analyze your crop'}
        icon={<Bug className="h-6 w-6" />}
      />

      <div className="card bg-gradient-to-r from-sky-50 to-primary-50 border-sky-200">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🤖</span>
          <div>
            <p className="font-bold text-charcoal-800">{language === 'te' ? 'AI-ఆధారిత విశ్లేషణ' : 'AI-Powered Analysis'}</p>
            <p className="text-sm text-charcoal-600">
              {language === 'te' ? 'HARVEX ఆకు చిత్రాల నుండి పంట ఆరోగ్యాన్ని అంచనా వేయడానికి NVIDIA Vision AI ని ఉపయోగిస్తుంది' : 'HARVEX uses NVIDIA Vision AI to assess crop health from leaf images'}
            </p>
          </div>
        </div>
      </div>

      {/* STEP 1: Crop Mode Selection */}
      {cropMode === null && !result && (
        <div className="space-y-4 animate-slide-up">
          <div className="card">
            <h3 className="font-bold text-charcoal-900 mb-2">
              {language === 'te' ? 'ఏ పంటను తనిఖీ చేస్తున్నారు?' : 'Whose crop are you checking?'}
            </h3>
            <p className="text-sm text-charcoal-500 mb-4">
              {language === 'te' ? 'మీ ప్రస్తుత పంట లేదా వేరే పంట కోసం ఆరోగ్య తనిఖీ చేయండి' : 'Check health for your current farming crop or a different crop'}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Option 1: My Present Crop */}
              <button
                onClick={() => handleModeSelect('present')}
                disabled={!activeCropName}
                className={`p-6 rounded-2xl border-2 text-left transition-all duration-200 ${
                  activeCropName
                    ? 'border-primary-400 hover:border-primary-500 hover:bg-primary-50 cursor-pointer'
                    : 'border-charcoal-200 bg-charcoal-50 cursor-not-allowed opacity-60'
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 bg-primary-100 rounded-2xl flex items-center justify-center">
                    <Sprout className="h-6 w-6 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-bold text-charcoal-900">
                      {language === 'te' ? 'నా ప్రస్తుత పంట' : 'My Present Crop'}
                    </p>
                    {activeCropName && (
                      <p className="text-sm text-primary-600 font-medium capitalize">
                        {activeCropName}
                      </p>
                    )}
                  </div>
                </div>
                {activeCropName ? (
                  <p className="text-sm text-charcoal-600">
                    {language === 'te'
                      ? `${activeCropName} ఆకు చిత్రాన్ని అప్‌లోడ్ చేసి విశ్లేషించండి`
                      : `Upload a ${activeCropName} leaf image for analysis`}
                  </p>
                ) : (
                  <p className="text-sm text-charcoal-500">
                    {language === 'te'
                      ? 'మొదలుగా పంటను ఎంచుకోండి. క్రాప్ సిఫార్సు నుండి మీ పంటను ఎంచుకోండి.'
                      : 'No active crop found. Please start farming a crop first.'}
                  </p>
                )}
              </button>

              {/* Option 2: Another Crop */}
              <button
                onClick={() => handleModeSelect('another')}
                className="p-6 rounded-2xl border-2 border-charcoal-200 hover:border-primary-300 hover:bg-primary-50 text-left transition-all duration-200 cursor-pointer"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 bg-harvest-100 rounded-2xl flex items-center justify-center">
                    <Search className="h-6 w-6 text-harvest-600" />
                  </div>
                  <div>
                    <p className="font-bold text-charcoal-900">
                      {language === 'te' ? 'వేరే పంట' : 'Another Crop'}
                    </p>
                  </div>
                </div>
                <p className="text-sm text-charcoal-600">
                  {language === 'te'
                    ? 'వేరే పంట ఆకును తనిఖీ చేయండి. ఇది మీ ప్రస్తుత పంటను మార్చదు.'
                    : 'Check a different crop. This will NOT change your active crop.'}
                </p>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2A: "My Present Crop" - auto-selected, show upload directly */}
      {cropMode === 'present' && activeCropName && !result && (
        <div className="space-y-4 animate-slide-up">
          <div className="card border-l-4 border-primary-400">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{getCropEmoji(activeCropName)}</span>
                <div>
                  <p className="text-sm text-charcoal-500">{language === 'te' ? 'ప్రస్తుత పంట' : 'Present Crop'}</p>
                  <p className="font-bold text-charcoal-900 capitalize">{activeCropName}</p>
                </div>
              </div>
              <button onClick={handleReset} className="btn-outline text-sm">
                {language === 'te' ? 'మార్చు' : 'Change'}
              </button>
            </div>
          </div>

          <div
            className={`card border-2 border-dashed transition-all duration-200 border-primary-400 hover:border-primary-500 cursor-pointer hover:bg-primary-50`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileSelect}
              className="hidden"
            />
            <div className="text-center py-12">
              <div className="w-20 h-20 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
                <Camera className="h-10 w-10 text-primary-600" />
              </div>
              <p className="text-xl font-bold text-charcoal-900 mb-2">
                {language === 'te' ? 'ఆకును స్కాన్ చేయడానికి నొక్కండి' : 'Tap to Scan Leaf'}
              </p>
              <p className="text-charcoal-500 mb-4">
                {language === 'te' ? 'మద్దతు: JPEG, PNG, WEBP (గరిష్టం 10MB)' : 'Supports: JPEG, PNG, WEBP (Max 10MB)'}
              </p>
              <button className="btn-secondary">
                <Upload className="h-4 w-4 inline mr-2" />
                {language === 'te' ? 'గ్యాలరీ నుండి అప్‌లోడ్ చేయండి' : 'Upload from Gallery'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2B: "Another Crop" - show crop selection grid */}
      {cropMode === 'another' && !result && (
        <div className="space-y-4 animate-slide-up">
          <div className="card border-l-4 border-harvest-400">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Search className="h-6 w-6 text-harvest-600" />
                <div>
                  <p className="text-sm text-charcoal-500">{language === 'te' ? 'వేరే పంట' : 'Another Crop'}</p>
                  <p className="font-bold text-charcoal-900">
                    {language === 'te' ? 'ఏ పంట ఆకును తనిఖీ చేయాలో ఎంచుకోండి' : 'Select which crop to check'}
                  </p>
                </div>
              </div>
              <button onClick={handleReset} className="btn-outline text-sm">
                {language === 'te' ? 'మార్చు' : 'Change'}
              </button>
            </div>
          </div>

          {activeCropName && (
            <div className="bg-info-50 border border-info-200 rounded-xl p-3 text-sm text-info-800">
              {language === 'te'
                ? `ℹ️ మీ ప్రస్తుత పంట ${activeCropName}. వేరే పంట ఎంపిక మీ ప్రస్తుత పంటను మార్చదు.`
                : `ℹ️ Your active crop is ${activeCropName}. Selecting another crop will NOT change it.`}
            </div>
          )}

          <div className="card">
            <label className="label">{language === 'te' ? 'పంటను ఎంచుకోండి' : 'Select crop to scan'}</label>
            <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
              {CROP_OPTIONS.map(c => (
                <button
                  key={c.value}
                  onClick={() => {
                    setSelectedCrop(c.value);
                    setResult(null);
                    setError('');
                  }}
                  className={`p-3 rounded-2xl border-2 transition-all duration-200 ${
                    selectedCrop === c.value
                      ? 'border-primary-500 bg-primary-50 shadow-soft'
                      : 'border-charcoal-200 hover:border-primary-300'
                  }`}
                >
                  <span className="text-2xl">{c.emoji}</span>
                  <p className="text-xs font-medium text-charcoal-700 mt-1">{language === 'te' ? c.labelTe : c.labelEn}</p>
                </button>
              ))}
            </div>
          </div>

          {selectedCrop && (
            <div
              className="card border-2 border-dashed border-primary-400 hover:border-primary-500 cursor-pointer hover:bg-primary-50 transition-all duration-200"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="text-center py-12">
                <div className="w-20 h-20 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
                  <Camera className="h-10 w-10 text-primary-600" />
                </div>
                <p className="text-xl font-bold text-charcoal-900 mb-2">
                  {language === 'te' ? 'ఆకును స్కాన్ చేయడానికి నొక్కండి' : 'Tap to Scan Leaf'}
                </p>
                <p className="text-charcoal-500 mb-4">
                  {language === 'te' ? 'మద్దతు: JPEG, PNG, WEBP (గరిష్టం 10MB)' : 'Supports: JPEG, PNG, WEBP (Max 10MB)'}
                </p>
                <button className="btn-secondary">
                  <Upload className="h-4 w-4 inline mr-2" />
                  {language === 'te' ? 'గ్యాలరీ నుండి అప్‌లోడ్ చేయండి' : 'Upload from Gallery'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Image Preview */}
      {preview && (
        <div className="card">
          <img src={preview} alt="Uploaded leaf" className="max-h-64 mx-auto rounded-2xl" />
        </div>
      )}

      {/* Loading State */}
      {modelLoading && (
        <div className="card text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
            <Loader2 className="h-8 w-8 text-primary-600 animate-spin" />
          </div>
          <h3 className="text-xl font-bold text-charcoal-900 mb-2">
            {t('examiningCrop') || 'HARVEX is examining your crop'}
          </h3>
          <p className="text-charcoal-500 mb-2">
            {t('pleaseWait') || 'Please wait while HARVEX analyzes your crop image...'}
          </p>
          {elapsed < 45 ? (
            <p className="text-charcoal-400 text-sm italic mb-6">
              {language === 'te'
                ? '🔬 HARVEX ఆకును జాగ్రత్తగా పరిశీలిస్తోంది. ఒక్క ఆకులోనే చాలా సంకేతాలు ఉండొచ్చు కదా! 😄🌿'
                : '🔬 HARVEX is carefully checking the leaf. Even one leaf can have a lot of clues! 😄🌿'}
            </p>
          ) : (
            <p className="text-amber-600 text-sm italic mb-6">
              {language === 'te'
                ? '🐢 సాధారణం కంటే కొంచెం ఎక్కువ సమయం పడుతోందా? మీ నెట్‌వర్క్ లేదా AI సేవ నెమ్మదిగా ఉండవచ్చు. మేము ఇంకా ఆకును పరిశీలిస్తున్నాము.'
                : '🐢 Taking a little longer than usual? Your network or AI service may be slow. We\'re still checking the leaf.'}
            </p>
          )}
          <div className="max-w-sm mx-auto space-y-3 text-left">
            {stages.map(stage => (
              <div key={stage.key} className="flex items-center gap-3">
                {stage.status === 'done' && <CheckCircle className="h-5 w-5 text-success shrink-0" />}
                {stage.status === 'active' && <Loader2 className="h-5 w-5 text-primary-500 animate-spin shrink-0" />}
                {stage.status === 'pending' && <div className="w-5 h-5 rounded-full border-2 border-charcoal-300 shrink-0" />}
                {stage.status === 'error' && <AlertTriangle className="h-5 w-5 text-danger shrink-0" />}
                <span className={`text-sm ${
                  stage.status === 'done' ? 'text-charcoal-700' :
                  stage.status === 'active' ? 'text-primary-600 font-medium' :
                  stage.status === 'error' ? 'text-danger' : 'text-charcoal-400'
                }`}>
                  {language === 'te' ? stage.labelTe : stage.labelEn}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="card bg-danger-light border-danger/20">
          <p className="text-danger-dark">{error}</p>
          <button onClick={() => { setError(''); setResult(null); }} className="btn-outline mt-3 text-sm">
            {language === 'te' ? 'మళ్ళీ ప్రయత్నించండి' : 'Try Again'}
          </button>
        </div>
      )}

      {/* Healthy Result */}
      {result && result.supported && isHealthy && (
        <div className="space-y-6 animate-slide-up">
          <div className="card border-l-4 border-success bg-success-light/30">
            <div className="flex items-start gap-4">
              <CheckCircle className="h-8 w-8 text-success-dark mt-1" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-charcoal-500 mb-1">{t('aiVisualAssessment')}</p>
                    <h2 className="text-2xl font-extrabold text-charcoal-900">{t('healthy')}</h2>
                    <p className="text-charcoal-600 mt-1">{result.crop}</p>
                  </div>
                  {result.confidence != null && (
                    <div className="text-right">
                      <div className="text-4xl font-extrabold text-success-600">
                        {(result.confidence * 100).toFixed(0)}%
                      </div>
                      <p className="text-sm text-charcoal-500">{t('confidence')}</p>
                    </div>
                  )}
                </div>
                {result.explanation && (
                  <div className="mt-4 p-4 bg-white/50 rounded-2xl">
                    <p className="text-sm text-charcoal-700">{result.explanation}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {result.visual_evidence && result.visual_evidence.length > 0 && (
            <div className="card">
              <h3 className="font-bold text-charcoal-900 mb-3">{t('visualEvidence')}</h3>
              <ul className="space-y-2">
                {result.visual_evidence.map((evidence, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-charcoal-700">
                    <span className="text-success-500 mt-1">●</span>
                    {evidence}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.treatment && (
            <div className="card border-l-4 border-success-400">
              <h3 className="font-bold text-charcoal-900 mb-3">{t('healthGuidance')}</h3>
              
              {result.treatment.cultural_or_organic_actions && result.treatment.cultural_or_organic_actions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-charcoal-700 mb-2">{t('culturalPractices')}</h4>
                  <ul className="space-y-1">
                    {result.treatment.cultural_or_organic_actions.map((action, i) => (
                      <li key={i} className="text-sm text-charcoal-600 flex items-start gap-2">
                        <span className="text-success-500">•</span> {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.treatment.follow_up_days && (
                <p className="text-sm text-charcoal-500">
                  {t('routineCheck')} {result.treatment.follow_up_days} {t('days')}.
                </p>
              )}
            </div>
          )}

          <div className="card bg-cream-100 border-cream-300">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-harvest-600 mt-0.5" />
              <p className="text-sm text-charcoal-700">{t('disclaimer')}</p>
            </div>
          </div>

          <div className="text-center">
            <button onClick={handleReset} className="btn-primary">
              {language === 'te' ? 'మరొక స్కాన్ చేయండి' : 'Scan Another Leaf'}
            </button>
          </div>
        </div>
      )}

      {/* Diseased Result */}
      {result && result.supported && isDiseased && (
        <div className="space-y-6 animate-slide-up">
          <div className="card border-l-4 border-danger bg-danger-light/30">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <span className="text-5xl">{getCropEmoji(selectedCrop)}</span>
                <div>
                  <p className="text-sm text-charcoal-500 mb-1">{t('aiVisualAssessment')}</p>
                  <h2 className="text-2xl font-extrabold text-charcoal-900">
                    {result.display_name || result.predicted_disease?.replace(/_/g, ' ')}
                  </h2>
                  <p className="text-charcoal-600 mt-1">{result.crop}</p>
                </div>
              </div>
              {result.confidence != null && (
                <div className="text-right">
                  <div className="text-4xl font-extrabold text-primary-600">
                    {(result.confidence * 100).toFixed(0)}%
                  </div>
                  <p className="text-sm text-charcoal-500">{t('confidence')}</p>
                </div>
              )}
            </div>

            <div className="mt-4 flex items-center gap-4">
              <span className={`badge ${getSeverityColor(result.severity || '')}`}>
                {t('severity')}: {language === 'te' ? ({'severe': t('severeSeverity'), 'moderate': t('moderateSeverity'), 'mild': t('mildSeverity'), 'none': t('noneSeverity')}[result.severity?.toLowerCase() as string] || result.severity) : result.severity}
              </span>
              <span className="text-sm text-charcoal-500">
                {t('provider')}: {result.provider} / {t('model')}: {result.model_name}
              </span>
            </div>

            {result.explanation && (
              <div className="mt-4 p-4 bg-white/50 rounded-2xl">
                <p className="text-sm text-charcoal-700">{result.explanation}</p>
              </div>
            )}
          </div>

          {result.visual_evidence && result.visual_evidence.length > 0 && (
            <div className="card">
              <h3 className="font-bold text-charcoal-900 mb-3">{t('visualEvidence')}</h3>
              <ul className="space-y-2">
                {result.visual_evidence.map((evidence, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-charcoal-700">
                    <span className="text-danger-500 mt-1">●</span>
                    {evidence}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.treatment && (
            <div className="card border-l-4 border-primary-400">
              <h3 className="font-bold text-charcoal-900 mb-3">{t('treatmentGuidance')}</h3>
              
              {result.treatment.immediate_actions && result.treatment.immediate_actions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-charcoal-700 mb-2">{t('immediateActions')}</h4>
                  <ul className="space-y-1">
                    {result.treatment.immediate_actions.map((action, i) => (
                      <li key={i} className="text-sm text-charcoal-600 flex items-start gap-2">
                        <span className="text-primary-500">•</span> {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.treatment.cultural_or_organic_actions && result.treatment.cultural_or_organic_actions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-charcoal-700 mb-2">{t('culturalPractices')}</h4>
                  <ul className="space-y-1">
                    {result.treatment.cultural_or_organic_actions.map((action, i) => (
                      <li key={i} className="text-sm text-charcoal-600 flex items-start gap-2">
                        <span className="text-success-500">•</span> {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.treatment.chemical_options && result.treatment.chemical_options.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-charcoal-700 mb-2">{t('chemicalControl')}</h4>
                  <ul className="space-y-1">
                    {result.treatment.chemical_options.map((opt, i) => (
                      <li key={i} className="text-sm text-charcoal-600 flex items-start gap-2">
                        <span className="text-warning-500">•</span> {opt}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.treatment.safety_note && (
                <div className="p-3 bg-warning-50 rounded-xl mb-3">
                  <p className="text-xs text-warning-800">
                    <Info className="h-3 w-3 inline mr-1" />
                    {result.treatment.safety_note}
                  </p>
                </div>
              )}

              {result.treatment.follow_up_days && (
                <p className="text-sm text-charcoal-500">
                  {t('followUpIn')} {result.treatment.follow_up_days} {t('days')}.
                  {result.treatment.reassessment_reason && ` ${result.treatment.reassessment_reason}`}
                </p>
              )}
            </div>
          )}

          {result.needs_follow_up && !result.treatment && (
            <div className="card bg-info-50 border-info-200">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-info-600 mt-0.5" />
                <div>
                  <p className="font-bold text-charcoal-900">{t('followUpRecommended')}</p>
                  <p className="text-sm text-charcoal-600">
                    {t('uploadAnother')}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="card bg-cream-100 border-cream-300">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-harvest-600 mt-0.5" />
              <p className="text-sm text-charcoal-700">{t('disclaimer')}</p>
            </div>
          </div>

          <div className="text-center">
            <button onClick={handleReset} className="btn-primary">
              {language === 'te' ? 'మరొక స్కాన్ చేయండి' : 'Scan Another Leaf'}
            </button>
          </div>
        </div>
      )}

      {/* Unable to Determine Result */}
      {result && result.supported && isUnableToDetermine && (
        <div className="space-y-6 animate-slide-up">
          <div className="card border-l-4 border-warning bg-warning-light/30">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-6 w-6 text-warning-dark mt-1" />
              <div>
                <h3 className="text-lg font-bold text-charcoal-900 mb-1">
                  {t('unableToDetermine')}
                </h3>
                <p className="text-charcoal-700">
                  {result.needs_better_image
                    ? (language === 'te' ? 'చిత్రంలో నమ్మదగిన మొక్క ఆరోగ్య అంచనా కోసం తగినంత స్పష్టమైన దృశ్య సమాచారం లేదు. దయచేసి ప్రభావిత ఆకు లేదా మొక్క భాగం యొక్క స్పష్టమైన దగ్గరి చిత్రాన్ని అప్‌లోడ్ చేయండి.'
                      : 'The image does not contain enough clear visual information for reliable plant-health assessment. Please upload a clear close-up image of the affected leaf or plant part.')
                    : result.description || result.explanation || (language === 'te' ? 'AI ఈ చిత్రం నుండి మొక్క ఆరోగ్యాన్ని నిర్ణయించలేకపోయింది. దయచేసి ప్రభావిత ఆకు యొక్క స్పష్టమైన ఫోటోను ప్రయత్నించండి.'
                      : 'AI was unable to determine the plant health from this image. Please try uploading a clearer photo of the affected leaf.')
                  }
                </p>
                <p className="text-sm text-charcoal-500 mt-2">
                  {t('tipClearPhoto')}
                </p>
              </div>
            </div>
          </div>

          {result.treatment && (
            <div className="card border-l-4 border-warning-400">
              <h3 className="font-bold text-charcoal-900 mb-3">{t('imageQualityGuidance')}</h3>
              
              {result.treatment.cultural_or_organic_actions && result.treatment.cultural_or_organic_actions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-charcoal-700 mb-2">{t('nextSteps')}</h4>
                  <ul className="space-y-1">
                    {result.treatment.cultural_or_organic_actions.map((action, i) => (
                      <li key={i} className="text-sm text-charcoal-600 flex items-start gap-2">
                        <span className="text-warning-500">•</span> {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.treatment.follow_up_days && (
                <p className="text-sm text-charcoal-500">
                  {t('tryAgainIn')} {result.treatment.follow_up_days} {t('days')} {t('clearerImage')}.
                </p>
              )}
            </div>
          )}

          <div className="text-center">
            <button onClick={handleReset} className="btn-primary">
              {language === 'te' ? 'మరొక స్కాన్ చేయండి' : 'Scan Another Leaf'}
            </button>
          </div>
        </div>
      )}

      {/* NVIDIA Unavailable */}
      {result && result.supported && result.quality_check?.quality === 'unavailable' && (
        <div className="card border-l-4 border-warning bg-warning-light/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 text-warning-dark mt-1" />
            <div>
              <h3 className="text-lg font-bold text-charcoal-900 mb-1">
                {t('aiUnavailableTitle')}
              </h3>
              <p className="text-charcoal-700">
                {result.description || t('nvidiaUnavailableDesc')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Unsupported Crop Result */}
      {result && !result.supported && (
        <div className="card border-l-4 border-warning bg-warning-light/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 text-warning-dark mt-1" />
            <div>
              <h3 className="text-lg font-bold text-charcoal-900 mb-1">
                {result.crop?.charAt(0).toUpperCase() + (result.crop?.slice(1) || '')} {t('detectionNotAvailable')}
              </h3>
              <p className="text-charcoal-700">{result.message}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
