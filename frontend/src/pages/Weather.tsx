import { useState, useEffect, useRef } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { useLanguage } from '../contexts/LanguageContext';
import { weatherAPI } from '../services/api';
import { Cloud, Droplets, Wind, Thermometer, MapPin, RefreshCw } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';

interface ForecastEntry {
  time: string;
  temperature: number;
  humidity: number;
  rain_probability: number;
  rainfall: number;
  wind_speed: number;
  condition: string;
}

export default function Weather() {
  const { farm, farmLoading } = useFarm();
  const { t, language } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [weather, setWeather] = useState<any>(null);
  const [forecast, setForecast] = useState<ForecastEntry[]>([]);
  const [error, setError] = useState('');
  const [weatherStatus, setWeatherStatus] = useState<'current' | 'cached' | 'unavailable'>('unavailable');

  const farmLoaded = useRef(false);

  useEffect(() => {
    if (farmLoaded.current) {
      loadWeather();
    }
  }, [farm?.latitude, farm?.longitude]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!farmLoading) {
      farmLoaded.current = true;
      loadWeather();
    }
    return () => { farmLoaded.current = false; };
  }, [farmLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadWeather = async () => {
    const lat = farm?.latitude;
    const lon = farm?.longitude;

    if (!lat || !lon) {
      setLoading(false);
      setWeatherStatus('unavailable');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const [currentRes, forecastRes] = await Promise.all([
        weatherAPI.getCurrent(lat, lon),
        weatherAPI.getForecast(lat, lon),
      ]);
      const currentData = currentRes.data;
      setWeather(currentData);
      setForecast(forecastRes.data?.forecast || []);

      if (currentData?.cached) {
        setWeatherStatus('cached');
      } else {
        setWeatherStatus('current');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Weather temporarily unavailable');
      setWeatherStatus('unavailable');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingState title={t('loadingWeather') || 'Loading weather...'} subtitle={t('fetchingWeather') || 'Fetching weather data for your farm'} />;
  }

  if (weatherStatus === 'unavailable' && !weather) {
    return (
      <div className="page-container">
        <PageHeader
          title={t('weather') || 'Weather Intelligence'}
          subtitle={t('farmWeather') || 'Weather data for your farm'}
          icon={<Cloud className="h-6 w-6" />}
        />
        <EmptyState
          icon="🌤️"
          title={!farm?.latitude ? (t('setFarmLocation') || 'Set your farm location') : (t('weatherUnavailable') || 'Weather temporarily unavailable')}
          description={!farm?.latitude
            ? (t('setLocationDesc') || 'Set your farm location to get weather information')
            : (t('weatherUnavailableDesc') || 'Unable to fetch weather data. Please try again.')}
          action={
            <button onClick={loadWeather} className="btn-primary">
              <RefreshCw className="h-4 w-4 inline mr-2" />
              {t('tryAgain') || 'Try Again'}
            </button>
          }
        />
      </div>
    );
  }

  const current = weather?.current || weather;
  const locationName = weather?.location?.name || farm?.location_name || '';

  return (
    <div className="page-container">
      <PageHeader
        title={t('weather') || 'Weather Intelligence'}
        subtitle={t('farmWeather') || 'Weather data for your farm'}
        icon={<Cloud className="h-6 w-6" />}
      />

      {weatherStatus === 'cached' && (
        <div className="bg-warning-light border border-warning/20 rounded-xl p-3 text-sm text-warning-dark mb-4">
          {t('cachedWeather') || 'CACHED WEATHER'} — {t('updated') || 'Updated'} {weather?.cache_age_minutes || '?'} {language === 'te' ? 'నిమిషాల క్రితం' : 'minutes ago'}
        </div>
      )}

      {error && (
        <div className="bg-danger-light border border-danger/20 rounded-xl p-3 text-sm text-danger-dark mb-4">
          {error}
        </div>
      )}

      <div className="card bg-gradient-to-br from-sky-400 to-sky-600 text-white overflow-hidden relative">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sky-100 text-sm font-medium">{weatherStatus === 'cached' ? (t('cachedWeather') || 'CACHED WEATHER') : (t('liveWeather') || 'LIVE WEATHER')}</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-6xl font-extrabold">{current.temperature}°C</span>
                <span className="text-2xl capitalize">{current.condition}</span>
              </div>
              {locationName && (
                <div className="flex items-center gap-1 mt-2 text-sky-200">
                  <MapPin className="h-4 w-4" />
                  <span className="text-sm">{locationName}</span>
                </div>
              )}
            </div>
            <span className="text-8xl hidden md:block">
              {getWeatherEmoji(current.condition)}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-6 mt-6 pt-6 border-t border-white/20">
            <div>
              <div className="flex items-center gap-2 text-sky-200 mb-1">
                <Droplets className="h-4 w-4" />
                <span className="text-sm">{t('humidity') || 'Humidity'}</span>
              </div>
              <p className="text-2xl font-bold">{current.humidity}%</p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sky-200 mb-1">
                <Cloud className="h-4 w-4" />
                <span className="text-sm">{t('rainfall') || 'Rainfall'}</span>
              </div>
              <p className="text-2xl font-bold">{current.rainfall || 0} mm</p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sky-200 mb-1">
                <Wind className="h-4 w-4" />
                <span className="text-sm">{language === 'te' ? 'గాలి' : 'Wind'}</span>
              </div>
              <p className="text-2xl font-bold">{current.wind_speed || 0} m/s</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card text-center">
          <Thermometer className="h-8 w-8 mx-auto text-danger mb-2" />
          <p className="text-sm text-charcoal-500">{t('temperature') || 'Temperature'}</p>
          <p className="text-3xl font-extrabold text-charcoal-900">{current.temperature}°C</p>
          <p className="text-sm text-charcoal-500 mt-1">
            {language === 'te' ? 'అనుభవం' : 'Feels like'} {current.feels_like || current.temperature}°C
          </p>
        </div>
        <div className="card text-center">
          <Droplets className="h-8 w-8 mx-auto text-sky-500 mb-2" />
          <p className="text-sm text-charcoal-500">{t('humidity') || 'Humidity'}</p>
          <p className="text-3xl font-extrabold text-charcoal-900">{current.humidity}%</p>
          <p className="text-sm text-charcoal-500 mt-1">
            {current.humidity > 70 ? (language === 'te' ? 'ఎక్కువ తేమ' : 'High humidity') : (language === 'te' ? 'మధ్యస్థ తేమ' : 'Moderate humidity')}
          </p>
        </div>
        <div className="card text-center">
          <Wind className="h-8 w-8 mx-auto text-charcoal-500 mb-2" />
          <p className="text-sm text-charcoal-500">{language === 'te' ? 'గాలి వేగం' : 'Wind Speed'}</p>
          <p className="text-3xl font-extrabold text-charcoal-900">{current.wind_speed || 0} m/s</p>
          <p className="text-sm text-charcoal-500 mt-1">
            {(current.wind_speed || 0) > 5 ? (language === 'te' ? 'బలమైన గాలులు' : 'Strong winds') : (language === 'te' ? 'తేలికపాటి గాలి' : 'Light breeze')}
          </p>
        </div>
      </div>

      {forecast.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-charcoal-900 mb-4">{language === 'te' ? '5-రోజుల సూచన' : '5-Day Forecast'}</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {forecast.slice(0, 5).map((entry, i) => (
              <div key={i} className="card text-center">
                <p className="text-sm text-charcoal-500">{formatDay(entry.time, language)}</p>
                <span className="text-3xl my-2 block">{getWeatherEmoji(entry.condition)}</span>
                <p className="font-bold text-charcoal-900">{entry.temperature}°C</p>
                <p className="text-xs text-charcoal-500">{entry.condition}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-center">
        <button onClick={loadWeather} className="btn-secondary">
          <RefreshCw className="h-4 w-4 inline mr-2" />
          {t('refreshWeather') || 'Refresh Weather'}
        </button>
      </div>
    </div>
  );
}

function getWeatherEmoji(condition: string) {
  const c = (condition || '').toLowerCase();
  if (c.includes('clear') || c.includes('sunny')) return '☀️';
  if (c.includes('cloud') && c.includes('part')) return '⛅';
  if (c.includes('cloud')) return '☁️';
  if (c.includes('rain') || c.includes('drizzle')) return '🌧️';
  if (c.includes('storm') || c.includes('thunder')) return '⛈️';
  if (c.includes('fog') || c.includes('mist')) return '🌫️';
  return '🌤️';
}

function formatDay(time: string, lang: string) {
  const date = new Date(time);
  if (lang === 'te') {
    const days = ['ఆది', 'సోమ', 'మంగళ', 'బుధ', 'గురు', 'శుక్ర', 'శని'];
    return days[date.getDay()] || date.toLocaleDateString('en-US', { weekday: 'short' });
  }
  return date.toLocaleDateString('en-US', { weekday: 'short' });
}
