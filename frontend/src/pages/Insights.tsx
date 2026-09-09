import { useState, useEffect, useCallback } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { useLanguage } from '../contexts/LanguageContext';
import { aiAPI } from '../services/api';
import { LineChart, Loader2, TrendingUp, Brain, Sprout, Droplets, AlertTriangle, RefreshCw } from 'lucide-react';
import PageHeader from '../components/PageHeader';

interface Insight {
  category: string;
  title: string;
  description: string;
  priority: string;
  source: string;
}

export default function Insights() {
  const { cropCycle } = useFarm();
  const { t, language } = useLanguage();

  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [summary, setSummary] = useState('');
  const [error, setError] = useState('');
  const [hasLoaded, setHasLoaded] = useState(false);

  const loadInsights = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await aiAPI.getInsights();
      const data = res.data;
      if (data && data.available && data.data) {
        setInsights(data.data.insights || []);
        setSummary(data.data.summary || '');
      } else if (data && !data.available) {
        setError(t('insightsUnavailable'));
      } else {
        setInsights([]);
        setSummary('');
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '';
      if (msg.includes('401') || msg.includes('Unauthorized')) {
        setError(t('insightsUnavailable'));
      } else {
        setError(t('insightsUnavailable'));
      }
    } finally {
      setLoading(false);
      setHasLoaded(true);
    }
  }, [t]);

  useEffect(() => {
    if (cropCycle && !hasLoaded) {
      loadInsights();
    }
  }, [cropCycle, hasLoaded, loadInsights]);

  if (!cropCycle) {
    return (
      <div className="page-container">
        <PageHeader
          title={t('insights')}
          subtitle={language === 'te' ? 'AI-ఆధారిత పొలం అంతర్దృష్టులు' : 'AI-generated intelligence for your farm'}
          icon={<LineChart className="h-6 w-6" />}
        />
        <div className="card text-center py-12">
          <div className="text-5xl mb-4">📊</div>
          <h3 className="text-lg font-bold text-charcoal-900 mb-2">{t('noActiveCropInsights')}</h3>
          <p className="text-charcoal-500">{t('noActiveCropInsightsDesc')}</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-container">
        <PageHeader
          title={t('insights')}
          subtitle={language === 'te' ? 'AI-ఆధారిత పొలం అంతర్దృష్టులు' : 'AI-generated intelligence for your farm'}
          icon={<LineChart className="h-6 w-6" />}
        />
        <div className="card text-center py-12">
          <Loader2 className="h-12 w-12 text-primary-500 animate-spin mx-auto mb-4" />
          <h3 className="text-lg font-bold text-charcoal-900 mb-2">{t('generatingInsights')}</h3>
          <p className="text-charcoal-500">{t('loadingInsights')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <PageHeader
          title={t('insights')}
          subtitle={language === 'te' ? 'AI-ఆధారిత పొలం అంతర్దృష్టులు' : 'AI-generated intelligence for your farm'}
          icon={<LineChart className="h-6 w-6" />}
        />
        <div className="card text-center py-12">
          <div className="text-5xl mb-4">⚠️</div>
          <h3 className="text-lg font-bold text-charcoal-900 mb-2">{t('insightsUnavailable')}</h3>
          <p className="text-charcoal-500 mb-4">{t('insightsUnavailableDesc')}</p>
          <button onClick={loadInsights} className="btn-primary">
            <RefreshCw className="h-4 w-4 inline mr-2" />
            {t('tryAgain')}
          </button>
        </div>
      </div>
    );
  }

  if (insights.length === 0 && !summary) {
    return (
      <div className="page-container">
        <PageHeader
          title={t('insights')}
          subtitle={language === 'te' ? 'AI-ఆధారిత పొలం అంతర్దృష్టులు' : 'AI-generated intelligence for your farm'}
          icon={<LineChart className="h-6 w-6" />}
        />
        <div className="card text-center py-12">
          <div className="text-5xl mb-4">💡</div>
          <h3 className="text-lg font-bold text-charcoal-900 mb-2">{t('noInsightsData')}</h3>
          <p className="text-charcoal-500 mb-4">{t('noInsightsDataDesc')}</p>
          <button onClick={loadInsights} className="btn-secondary">
            <RefreshCw className="h-4 w-4 inline mr-2" />
            {t('refreshInsights')}
          </button>
        </div>
      </div>
    );
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'crop': return <Sprout className="h-5 w-5 text-primary-600" />;
      case 'financial': return <TrendingUp className="h-5 w-5 text-harvest-600" />;
      case 'water': return <Droplets className="h-5 w-5 text-sky-600" />;
      case 'risk': return <AlertTriangle className="h-5 w-5 text-danger" />;
      default: return <Brain className="h-5 w-5 text-purple-600" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'crop': return 'bg-primary-100 text-primary-700';
      case 'financial': return 'bg-harvest-100 text-harvest-700';
      case 'water': return 'bg-sky-100 text-sky-700';
      case 'risk': return 'bg-danger-light text-danger-dark';
      default: return 'bg-purple-100 text-purple-700';
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title={t('insights')}
        subtitle={language === 'te' ? 'AI-ఆధారిత పొలం అంతర్దృష్టులు' : 'AI-generated intelligence for your farm'}
        icon={<LineChart className="h-6 w-6" />}
      />

      {summary && (
        <div className="card bg-gradient-to-r from-primary-50 to-sky-50 border-primary-200">
          <div className="flex items-start gap-3">
            <Brain className="h-6 w-6 text-primary-600 mt-0.5" />
            <div>
              <p className="font-bold text-charcoal-900">{t('aiSummary')}</p>
              <p className="text-charcoal-700 mt-1">{summary}</p>
            </div>
          </div>
        </div>
      )}

      {insights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {insights.map((insight, i) => (
            <div key={i} className="card-hover animate-slide-up" style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${getCategoryColor(insight.category)}`}>
                  {getCategoryIcon(insight.category)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-charcoal-900">{insight.title}</h3>
                    <span className={`badge ${
                      insight.priority === 'high' ? 'badge-danger' :
                      insight.priority === 'medium' ? 'badge-warning' : 'badge-success'
                    }`}>
                      {insight.priority}
                    </span>
                  </div>
                  <p className="text-sm text-charcoal-600 mt-2">{insight.description}</p>
                  <p className="text-xs text-charcoal-400 mt-2">{t('insightSource')}: {insight.source}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="text-center">
        <button onClick={loadInsights} className="btn-secondary">
          <RefreshCw className="h-4 w-4 inline mr-2" />
          {t('refreshInsights')}
        </button>
      </div>
    </div>
  );
}
