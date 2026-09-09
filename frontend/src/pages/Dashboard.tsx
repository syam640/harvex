import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useFarm } from '../contexts/FarmContext';
import { useLanguage } from '../contexts/LanguageContext';
import { decisionAPI, weatherAPI, expensesAPI } from '../services/api';
import { 
  Cloud, Sprout, IndianRupee, TrendingUp, 
  Brain, Camera, Wheat, MessageCircle, ArrowRight, Calendar, Receipt
} from 'lucide-react';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import WeatherCard from '../components/WeatherCard';
import ActionCard from '../components/ActionCard';

interface DecisionResult {
  recommended_action: string;
  overall_score: number;
  reasoning: { reasons: string[] };
}

export default function Dashboard() {
  const { user } = useAuth();
  const { farm, field, cropCycle, farmLoading } = useFarm();
  const { t, language } = useLanguage();
  const navigate = useNavigate();

  const [weather, setWeather] = useState<any>(null);
  const [decision, setDecision] = useState<DecisionResult | null>(null);
  const [totalExpenses, setTotalExpenses] = useState(0);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return t('goodMorning');
    if (hour < 17) return t('goodAfternoon');
    return t('goodEvening');
  };

  useEffect(() => {
    if (cropCycle) {
      loadDecisionAndWeather();
    }
  }, [cropCycle?.id]);

  const loadDecisionAndWeather = async () => {
    if (!cropCycle || !farm) return;
    try {
      const [decisionRes, expensesRes] = await Promise.all([
        decisionAPI.analyze({ crop_cycle_id: cropCycle.id }),
        expensesAPI.getExpenses(cropCycle.id).catch(() => ({ data: [] })),
      ]);
      
      setDecision(decisionRes.data);
      setTotalExpenses(expensesRes.data.reduce((sum: number, e: any) => sum + (e.amount || 0), 0));

      if (farm.latitude && farm.longitude) {
        try {
          const weatherRes = await weatherAPI.getCurrent(farm.latitude, farm.longitude);
          setWeather(weatherRes.data);
        } catch {}
      }
    } catch (err) {
      console.error('Failed to load decision/weather:', err);
    }
  };

  if (farmLoading) {
    return <LoadingState title={language === 'te' ? 'మీ పొలం లోడ్ అవుతోంది...' : 'Loading your farm...'} subtitle={language === 'te' ? 'HARVEX మీ పొలం డేటాను తనిఖీ చేస్తోంది' : 'HARVEX is checking your farm data'} />;
  }

  if (!farm || !field) {
    return (
      <div className="page-container">
        <EmptyState
          icon="🌱"
          title={language === 'te' ? 'HARVEX కు స్వాగతం!' : 'Welcome to HARVEX!'}
          description={language === 'te' ? 'వ్యవసాయ తెలివితేటలు మరియు AI-ఆధారిత అంతర్దృష్టులను అన్లాక్ చేయడానికి మీ మొదటి పంటను ప్రారంభించండి.' : 'Start your first crop to unlock farm intelligence and AI-powered insights.'}
          action={
            <button onClick={() => navigate('/crop-recommendation-intelligent')} className="btn-primary btn-pill text-lg">
              <Sprout className="h-5 w-5 inline mr-2" />
              {language === 'te' ? 'పంట సిఫార్సు పొందండి' : 'Get Crop Recommendation'}
            </button>
          }
        />
      </div>
    );
  }

  const daysActive = cropCycle?.planting_date 
    ? Math.floor((Date.now() - new Date(cropCycle.planting_date).getTime()) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="page-container">
      {/* Greeting */}
      <div className="animate-fade-in">
        <h1 className="text-3xl font-extrabold text-charcoal-900">
          {getGreeting()}, {user?.name?.split(' ')[0]}! 👋
        </h1>
        <p className="text-charcoal-500 mt-1">{language === 'te' ? 'మీ పొలం అవలోకనం' : "Here's your farm overview"}</p>
      </div>

      {/* Active Crop Hero — shown immediately from context */}
      {cropCycle && (
        <div className="card bg-gradient-to-br from-primary-500 to-primary-700 text-white animate-slide-up">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-6xl">🌱</span>
              <div>
                <p className="text-primary-100 text-sm font-medium">{t('currentCrop')}</p>
                <h2 className="text-3xl font-extrabold">{cropCycle.crop_name}</h2>
                <p className="text-primary-200 mt-1">{language === 'te' ? 'రోజు' : 'Day'} {daysActive}</p>
              </div>
            </div>
            {weather && (
              <div className="text-right hidden md:block">
                <p className="text-4xl font-extrabold">{weather.current?.temperature || '--'}°C</p>
                <p className="text-primary-200 capitalize">{weather.current?.condition || ''}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* No active crop */}
      {!cropCycle && (
        <div className="card bg-amber-50 border-amber-200">
          <div className="flex items-center gap-3">
            <Sprout className="h-6 w-6 text-amber-600" />
            <div>
              <p className="font-bold text-amber-800">{t('noActiveCrop') || 'No active crop'}</p>
              <p className="text-sm text-amber-700">{t('startCropToTrack') || 'Start a crop to track expenses'}</p>
            </div>
            <button onClick={() => navigate('/crop-recommendation-intelligent')} className="btn-primary ml-auto text-sm">
              <Sprout className="h-4 w-4 inline mr-1" />
              {language === 'te' ? 'పంట సిఫార్సు' : 'Crop AI'}
            </button>
          </div>
        </div>
      )}

      {/* Today's Decision — loads independently */}
      {decision && (
        <div className="card-highlight animate-slide-up" style={{ animationDelay: '0.1s' }}>
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-primary-100 rounded-2xl flex items-center justify-center flex-shrink-0">
              <Brain className="h-7 w-7 text-primary-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-charcoal-500 font-medium">{t('todayDecision')}</p>
              <h3 className="text-xl font-bold text-charcoal-900 mt-1">{decision.recommended_action}</h3>
              {decision.reasoning?.reasons?.[0] && (
                <p className="text-charcoal-600 mt-2">{decision.reasoning.reasons[0]}</p>
              )}
              <button 
                onClick={() => navigate('/decisions')} 
                className="mt-3 text-primary-600 font-semibold text-sm flex items-center gap-1 hover:text-primary-700"
              >
                {t('viewDetails') || 'View Details'} <ArrowRight className="h-4 w-4" />
              </button>
            </div>
            <div className="text-right hidden md:block">
              <div className="text-3xl font-extrabold text-primary-600">{Math.round(decision.overall_score)}</div>
              <p className="text-xs text-charcoal-500">{language === 'te' ? 'స్కోర్' : 'Score'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
        <ActionCard 
          icon={<Sprout className="h-6 w-6" />}
          title={t('cropRecommendation')}
          path="/crop-recommendation-intelligent"
          color="bg-primary-100 text-primary-700"
        />
        <ActionCard 
          icon={<Camera className="h-6 w-6" />}
          title={t('disease')}
          path="/disease"
          color="bg-danger-light text-danger-dark"
        />
        <ActionCard 
          icon={<Cloud className="h-6 w-6" />}
          title={t('weather')}
          path="/weather"
          color="bg-sky-100 text-sky-700"
        />
        <ActionCard 
          icon={<MessageCircle className="h-6 w-6" />}
          title={t('assistant')}
          path="/assistant"
          color="bg-harvest-100 text-harvest-700"
        />
      </div>

      {/* Weather Card — loads independently */}
      {weather?.current && (
        <div className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
          <WeatherCard
            temperature={weather.current.temperature}
            condition={weather.current.condition}
            humidity={weather.current.humidity}
            rainfall={weather.current.rainfall || 0}
            windSpeed={weather.current.wind_speed || 0}
            location={farm.location_name || ''}
          />
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-slide-up" style={{ animationDelay: '0.4s' }}>
        <div className="card text-center">
          <div className="w-12 h-12 mx-auto bg-primary-100 rounded-2xl flex items-center justify-center mb-3">
            <Sprout className="h-6 w-6 text-primary-600" />
          </div>
          <p className="text-sm text-charcoal-500">{t('currentCrop')}</p>
          <p className="font-bold text-charcoal-900">{cropCycle?.crop_name || '--'}</p>
        </div>
        <div className="card text-center">
          <div className="w-12 h-12 mx-auto bg-sky-100 rounded-2xl flex items-center justify-center mb-3">
            <Calendar className="h-6 w-6 text-sky-600" />
          </div>
          <p className="text-sm text-charcoal-500">{language === 'te' ? 'సక్రియ రోజులు' : 'Days Active'}</p>
          <p className="font-bold text-charcoal-900">{language === 'te' ? 'రోజు' : 'Day'} {daysActive}</p>
        </div>
        <div className="card text-center">
          <div className="w-12 h-12 mx-auto bg-harvest-100 rounded-2xl flex items-center justify-center mb-3">
            <IndianRupee className="h-6 w-6 text-harvest-600" />
          </div>
          <p className="text-sm text-charcoal-500">{t('totalExpenses')}</p>
          <p className="font-bold text-charcoal-900">₹{totalExpenses.toLocaleString()}</p>
        </div>
        <div className="card text-center">
          <div className="w-12 h-12 mx-auto bg-purple-100 rounded-2xl flex items-center justify-center mb-3">
            <TrendingUp className="h-6 w-6 text-purple-600" />
          </div>
          <p className="text-sm text-charcoal-500">{language === 'te' ? 'నిర్ణయ స్కోర్' : 'Decision Score'}</p>
          <p className="font-bold text-charcoal-900">{decision ? Math.round(decision.overall_score) : '--'}</p>
        </div>
      </div>

      {/* More Actions */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 animate-slide-up" style={{ animationDelay: '0.5s' }}>
        <ActionCard 
          icon={<Brain className="h-6 w-6" />}
          title={t('decisions')}
          path="/decisions"
          color="bg-purple-100 text-purple-700"
        />
        <ActionCard 
          icon={<Receipt className="h-6 w-6" />}
          title={t('expenses')}
          path="/expenses"
          color="bg-harvest-100 text-harvest-700"
        />
        <ActionCard 
          icon={<Wheat className="h-6 w-6" />}
          title={t('harvest')}
          path="/harvest"
          color="bg-primary-100 text-primary-700"
        />
      </div>
    </div>
  );
}
