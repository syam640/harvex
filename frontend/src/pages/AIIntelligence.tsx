import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { aiAPI, parseApiError } from '../services/api';
import { Brain, Sprout, Bug, Droplets, IndianRupee, TrendingUp, Loader2, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/PageHeader';

interface CardResult {
  available: boolean;
  data?: any;
  error?: string;
}

export default function AIIntelligence() {
  const navigate = useNavigate();
  const { t, language } = useLanguage();
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, CardResult>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  const handleClick = async (type: string, apiCall: () => Promise<any>) => {
    if (expanded === type) {
      setExpanded(null);
      return;
    }
    if (results[type] && !results[type].error) {
      setExpanded(type);
      return;
    }
    setLoading(type);
    setExpanded(null);
    try {
      const res = await apiCall();
      const body = res.data;
      if (body && body.available && body.data) {
        setResults({ ...results, [type]: { available: true, data: body.data } });
      } else if (body && !body.available) {
        setResults({ ...results, [type]: { available: false, error: body.message || t('insightsUnavailable') } });
      } else {
        setResults({ ...results, [type]: { available: false, error: t('resultUnavailable') } });
      }
      setExpanded(type);
    } catch (err: any) {
      setResults({ ...results, [type]: { available: false, error: parseApiError(err) } });
      setExpanded(type);
    } finally {
      setLoading(null);
    }
  };

  const renderResult = (type: string, data: any) => {
    if (!data) return null;
    switch (type) {
      case 'crop':
        return (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-charcoal-500">{t('recommendedCrop')}</span><span className="font-bold text-charcoal-900">{data.recommended_crop}</span></div>
            <div className="flex justify-between"><span className="text-charcoal-500">{t('suitability')}</span><span className="font-bold text-charcoal-900">{data.suitability}</span></div>
            {data.water_requirement && <div className="flex justify-between"><span className="text-charcoal-500">{t('waterRequirement')}</span><span className="font-bold text-charcoal-900">{data.water_requirement}</span></div>}
            {data.climate_suitability && <div className="flex justify-between"><span className="text-charcoal-500">{t('climateCompatibility')}</span><span className="font-bold text-charcoal-900">{data.climate_suitability}</span></div>}
            {data.reasons?.length > 0 && <div><p className="text-charcoal-500 mb-1">{language === 'te' ? 'కారణాలు' : 'Reasons'}</p><ul className="list-disc list-inside text-charcoal-700">{data.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul></div>}
            {data.major_risks?.length > 0 && <div><p className="text-charcoal-500 mb-1">{t('majorRisks')}</p><ul className="list-disc list-inside text-danger-dark">{data.major_risks.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul></div>}
          </div>
        );
      case 'risk':
        return (
          <div className="space-y-2 text-sm">
            {data.overall_risk && <div className="flex justify-between"><span className="text-charcoal-500">{t('overallRisk')}</span><span className={`font-bold ${data.overall_risk === 'HIGH' ? 'text-danger' : data.overall_risk === 'MEDIUM' ? 'text-harvest-600' : 'text-primary-600'}`}>{data.overall_risk}</span></div>}
            {data.key_concerns?.length > 0 && <div><p className="text-charcoal-500 mb-1">{t('keyConcerns')}</p><ul className="list-disc list-inside text-charcoal-700">{data.key_concerns.map((c: string, i: number) => <li key={i}>{c}</li>)}</ul></div>}
            {data.urgent_actions?.length > 0 && <div><p className="text-charcoal-500 mb-1">{t('urgentActions')}</p><ul className="list-disc list-inside text-charcoal-700">{data.urgent_actions.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul></div>}
          </div>
        );
      case 'irrigation':
        return (
          <div className="space-y-2 text-sm">
            {data.recommendation && <div className="flex justify-between"><span className="text-charcoal-500">{t('irrigationRecommendation')}</span><span className="font-bold text-charcoal-900">{data.recommendation}</span></div>}
            {data.confidence && <div className="flex justify-between"><span className="text-charcoal-500">{t('confidence')}</span><span className="font-bold text-charcoal-900">{data.confidence}</span></div>}
            {data.reasons?.length > 0 && <div><p className="text-charcoal-500 mb-1">{language === 'te' ? 'కారణాలు' : 'Reasons'}</p><ul className="list-disc list-inside text-charcoal-700">{data.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul></div>}
          </div>
        );
      case 'financial':
        return (
          <div className="space-y-2 text-sm">
            {data.total_expenses !== undefined && <div className="flex justify-between"><span className="text-charcoal-500">{t('totalExpensesLabel')}</span><span className="font-bold text-charcoal-900">Rs.{data.total_expenses}</span></div>}
            {data.total_revenue !== undefined && <div className="flex justify-between"><span className="text-charcoal-500">{t('totalRevenueLabel')}</span><span className="font-bold text-charcoal-900">Rs.{data.total_revenue}</span></div>}
            {data.net_profit !== undefined && <div className="flex justify-between"><span className="text-charcoal-500">{language === 'te' ? 'నికర లాభం' : 'Net Profit'}</span><span className={`font-bold ${data.net_profit >= 0 ? 'text-primary-600' : 'text-danger'}`}>Rs.{data.net_profit}</span></div>}
            {data.analysis && <p className="text-charcoal-600 mt-2">{typeof data.analysis === 'string' ? data.analysis : JSON.stringify(data.analysis)}</p>}
          </div>
        );
      case 'insights':
        return (
          <div className="space-y-3 text-sm">
            {data.summary && <p className="text-charcoal-700 font-medium">{data.summary}</p>}
            {data.insights?.map((insight: any, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`badge text-xs ${
                  insight.priority === 'high' ? 'badge-danger' :
                  insight.priority === 'medium' ? 'badge-warning' : 'badge-success'
                }`}>{insight.priority}</span>
                <div>
                  <p className="font-medium text-charcoal-900">{insight.title}</p>
                  <p className="text-charcoal-600">{insight.description}</p>
                </div>
              </div>
            ))}
          </div>
        );
      default:
        return <pre className="text-xs text-charcoal-600 whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre>;
    }
  };

  const cards = [
    {
      id: 'crop',
      icon: <Sprout className="h-6 w-6" />,
      title: t('cropRecommendationResult'),
      description: language === 'te' ? 'మీ పొలం సందర్భం ఆధారంగా AI-ఆధారిత పంట సూచనలు' : 'Get AI-powered crop suggestions based on your farm context',
      color: 'bg-primary-100 text-primary-700',
      apiCall: () => aiAPI.getCropRecommendation(),
    },
    {
      id: 'risk',
      icon: <Brain className="h-6 w-6" />,
      title: t('riskAnalysisResult'),
      description: language === 'te' ? 'మీ పంటకు సంభావ్య ప్రమాదాలను విశ్లేషించండి' : 'Analyze potential risks to your crop',
      color: 'bg-danger-light text-danger-dark',
      apiCall: () => aiAPI.getRisk(),
    },
    {
      id: 'irrigation',
      icon: <Droplets className="h-6 w-6" />,
      title: t('irrigationAdviceResult'),
      description: language === 'te' ? 'AI-ఆధారిత నీటిపారుదల సూచనలు పొందండి' : 'Get AI-driven irrigation recommendations',
      color: 'bg-sky-100 text-sky-700',
      apiCall: () => aiAPI.getIrrigation(),
    },
    {
      id: 'financial',
      icon: <IndianRupee className="h-6 w-6" />,
      title: t('financialAnalysisResult'),
      description: language === 'te' ? 'మీ పొలం ఆర్థిక విశ్లేషణ మరియు లాభదాయకత' : 'Analyze your farm finances and profitability',
      color: 'bg-harvest-100 text-harvest-700',
      apiCall: () => aiAPI.getFinancial(),
    },
    {
      id: 'insights',
      icon: <TrendingUp className="h-6 w-6" />,
      title: t('farmInsightsResult'),
      description: language === 'te' ? 'మీ పొలం గురించి AI-జనరేటెడ్ అంతర్దృష్టులు' : 'Get AI-generated insights about your farm',
      color: 'bg-purple-100 text-purple-700',
      apiCall: () => aiAPI.getInsights(),
    },
    {
      id: 'disease',
      icon: <Bug className="h-6 w-6" />,
      title: t('diseaseDetection'),
      description: language === 'te' ? 'AI విశ్లేషణ కోసం ఆకు చిత్రం అప్లోడ్ చేయండి' : 'Upload a leaf image for AI analysis',
      color: 'bg-danger-light text-danger-dark',
      apiCall: async () => { navigate('/disease'); return { data: null }; },
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title={t('aiIntelligence')}
        subtitle={language === 'te' ? 'NVIDIA NIM-ఆధారిత పొలం తెలివితేట' : 'NVIDIA NIM-powered farm intelligence'}
        icon={<Brain className="h-6 w-6" />}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map(card => {
          const result = results[card.id];
          const isExpanded = expanded === card.id;
          const isLoading = loading === card.id;
          const hasResult = result && !result.error;

          return (
            <div key={card.id} className="overflow-hidden">
              <div
                onClick={() => handleClick(card.id, card.apiCall)}
                className={`card-hover cursor-pointer group ${isExpanded ? 'rounded-b-none border-b-0' : ''}`}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(card.id, card.apiCall); } }}
                aria-expanded={isExpanded}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-14 h-14 ${card.color} rounded-2xl flex items-center justify-center
                                   group-hover:scale-110 transition-transform duration-200`}>
                      {card.icon}
                    </div>
                    <div>
                      <h3 className="font-bold text-charcoal-900 group-hover:text-primary-600 transition-colors">
                        {card.title}
                      </h3>
                      <p className="text-sm text-charcoal-500 mt-1">{card.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isLoading && <Loader2 className="h-5 w-5 text-primary-500 animate-spin" />}
                    {!isLoading && hasResult && (
                      isExpanded ? <ChevronUp className="h-5 w-5 text-charcoal-400" /> : <ChevronDown className="h-5 w-5 text-charcoal-400" />
                    )}
                  </div>
                </div>

                {!isLoading && !hasResult && !result?.error && (
                  <div className="mt-3 pt-3 border-t border-charcoal-100">
                    <p className="text-xs text-charcoal-400">{language === 'te' ? 'క్లిక్ చేసి విశ్లేషణ పొందండి' : 'Click to analyze'}</p>
                  </div>
                )}

                {result?.error && (
                  <div className="mt-3 pt-3 border-t border-danger/20">
                    <div className="flex items-center gap-2 text-danger-dark">
                      <AlertTriangle className="h-4 w-4" />
                      <p className="text-xs">{result.error}</p>
                    </div>
                  </div>
                )}
              </div>

              {isExpanded && hasResult && (
                <div className="card rounded-t-none border-t-0 p-4 bg-charcoal-50/50">
                  {renderResult(card.id, result.data)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
