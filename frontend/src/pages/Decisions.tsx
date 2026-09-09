import { useState, useEffect } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { decisionAPI, parseApiError } from '../services/api';
import { Brain, TrendingUp, AlertTriangle, Droplets, IndianRupee, Leaf, RefreshCw } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';

interface DecisionResult {
  recommended_action: string;
  overall_score: number;
  component_scores: {
    profit: number;
    risk: number;
    cost: number;
    water: number;
    sustainability: number;
  };
  reasoning: {
    reasons: string[];
  };
}

const scoreIcons: Record<string, any> = {
  profit: TrendingUp,
  risk: AlertTriangle,
  cost: IndianRupee,
  water: Droplets,
  sustainability: Leaf,
};

const scoreColors: Record<string, string> = {
  profit: 'bg-success-light text-success-dark',
  risk: 'bg-danger-light text-danger-dark',
  cost: 'bg-harvest-light text-harvest-dark',
  water: 'bg-sky-100 text-sky-700',
  sustainability: 'bg-primary-100 text-primary-700',
};

export default function Decisions() {
  const { cropCycle } = useFarm();

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DecisionResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (cropCycle) analyzeDecision();
  }, [cropCycle]);

  const analyzeDecision = async () => {
    if (!cropCycle) return;
    setLoading(true);
    setError('');
    try {
      const res = await decisionAPI.analyze({ crop_cycle_id: cropCycle.id });
      setResult(res.data);
    } catch (err: any) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!cropCycle) {
    return (
      <div className="page-container">
        <EmptyState
          icon="🧠"
          title="No active crop"
          description="Start a crop to get AI-powered decision analysis"
        />
      </div>
    );
  }

  if (loading) {
    return <LoadingState title="Analyzing your farm..." subtitle="HARVEX is computing the best decision" />;
  }

  return (
    <div className="page-container">
      <PageHeader 
        title="Today's Decision" 
        subtitle="AI-powered farming decision analysis"
        icon={<Brain className="h-6 w-6" />}
        action={
          <button onClick={analyzeDecision} className="btn-secondary">
            <RefreshCw className="h-4 w-4 inline mr-2" />
            Refresh
          </button>
        }
      />

      {error && (
        <div className="card bg-danger-light border-danger/20">
          <p className="text-danger-dark">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* Main Decision */}
          <div className="card bg-gradient-to-br from-primary-500 to-primary-700 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-primary-100 text-sm font-medium">Recommended Action</p>
                <h2 className="text-3xl font-extrabold mt-1">{result.recommended_action}</h2>
              </div>
              <div className="text-right">
                <div className="text-5xl font-extrabold">{Math.round(result.overall_score)}</div>
                <p className="text-primary-200">Overall Score</p>
              </div>
            </div>
          </div>

          {/* Component Scores */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(result.component_scores).map(([key, value]) => {
              const Icon = scoreIcons[key];
              return (
                <div key={key} className="card text-center">
                  <div className={`w-12 h-12 mx-auto rounded-2xl flex items-center justify-center mb-2 ${scoreColors[key]}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <p className="text-sm text-charcoal-500 capitalize">{key}</p>
                  <p className="text-2xl font-extrabold text-charcoal-900">{Math.round(value)}</p>
                </div>
              );
            })}
          </div>

          {/* Reasoning */}
          {result.reasoning?.reasons && result.reasoning.reasons.length > 0 && (
            <div className="card">
              <h3 className="font-bold text-charcoal-900 mb-4 flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary-600" />
                Why This Decision?
              </h3>
              <ul className="space-y-3">
                {result.reasoning.reasons.map((reason, i) => (
                  <li key={i} className="flex items-start gap-3 p-3 bg-charcoal-50 rounded-xl">
                    <span className="w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-charcoal-700">{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
