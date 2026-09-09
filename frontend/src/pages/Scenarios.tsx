import { useState, useEffect } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { scenariosAPI, decisionAPI, parseApiError } from '../services/api';
import { GitCompare, Plus, Loader2 } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';

interface Scenario {
  id: number;
  scenario_name: string;
  overall_score: number;
  component_scores: {
    profit: number;
    risk: number;
    cost: number;
    water: number;
    sustainability: number;
  };
  recommendation: string;
}

interface DecisionResult {
  overall_score: number;
  component_scores: {
    profit: number;
    risk: number;
    cost: number;
    water: number;
    sustainability: number;
  };
  recommended_action: string;
}

export default function Scenarios() {
  const { cropCycle } = useFarm();

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [currentDecision, setCurrentDecision] = useState<DecisionResult | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    scenario_name: '',
    scenario_changes: {
      heavy_rain: false,
      more_irrigation: false,
      higher_cost: false,
      disease_severity: 'low',
      temperature_change: 0,
    },
  });

  useEffect(() => {
    if (cropCycle) {
      loadScenarios();
      loadCurrentDecision();
    }
  }, [cropCycle]);

  const loadScenarios = async () => {
    if (!cropCycle) return;
    setLoading(true);
    try {
      const res = await scenariosAPI.getScenarios(cropCycle.id);
      setScenarios(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCurrentDecision = async () => {
    if (!cropCycle) return;
    try {
      const res = await decisionAPI.analyze({ crop_cycle_id: cropCycle.id });
      setCurrentDecision(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cropCycle) return;
    setCreating(true);
    setError('');
    try {
      await scenariosAPI.createScenario({
        crop_cycle_id: cropCycle.id,
        scenario_name: form.scenario_name,
        input_changes: form.scenario_changes,
      });
      setShowForm(false);
      setForm({ scenario_name: '', scenario_changes: { heavy_rain: false, more_irrigation: false, higher_cost: false, disease_severity: 'low', temperature_change: 0 } });
      loadScenarios();
    } catch (err: any) {
      setError(parseApiError(err));
    } finally {
      setCreating(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success-dark';
    if (score >= 60) return 'text-harvest-dark';
    return 'text-danger-dark';
  };

  if (!cropCycle) {
    return (
      <div className="page-container">
        <EmptyState
          icon="🔮"
          title="No active crop"
          description="Start a crop to explore what-if scenarios"
        />
      </div>
    );
  }

  return (
    <div className="page-container">
      <PageHeader 
        title="What If?" 
        subtitle="What changes if farm conditions change?"
        icon={<GitCompare className="h-6 w-6" />}
        action={
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">
            <Plus className="h-4 w-4 inline mr-2" />
            New Scenario
          </button>
        }
      />

      {error && (
        <div className="card bg-danger-light border-danger/20">
          <p className="text-danger-dark">{error}</p>
        </div>
      )}

      {/* Current Decision */}
      {currentDecision && (
        <div className="card bg-gradient-to-br from-charcoal-800 to-charcoal-900 text-white">
          <p className="text-charcoal-300 text-sm">Current Decision</p>
          <div className="flex items-center justify-between mt-2">
            <h3 className="text-xl font-bold">{currentDecision.recommended_action}</h3>
            <span className="text-3xl font-extrabold">{Math.round(currentDecision.overall_score)}</span>
          </div>
        </div>
      )}

      {/* Create Form */}
      {showForm && (
        <div className="card animate-slide-up">
          <h3 className="font-bold text-charcoal-900 mb-4">Create What-If Scenario</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="label">Scenario Name</label>
              <input
                type="text"
                value={form.scenario_name}
                onChange={(e) => setForm({ ...form, scenario_name: e.target.value })}
                className="input-field"
                placeholder="e.g., Heavy Rain Scenario"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex items-center gap-3 p-3 bg-charcoal-50 rounded-xl cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.scenario_changes.heavy_rain}
                  onChange={(e) => setForm({
                    ...form,
                    scenario_changes: { ...form.scenario_changes, heavy_rain: e.target.checked }
                  })}
                  className="w-5 h-5 text-primary-600 rounded"
                />
                <span>🌧️ Heavy Rain</span>
              </label>
              <label className="flex items-center gap-3 p-3 bg-charcoal-50 rounded-xl cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.scenario_changes.more_irrigation}
                  onChange={(e) => setForm({
                    ...form,
                    scenario_changes: { ...form.scenario_changes, more_irrigation: e.target.checked }
                  })}
                  className="w-5 h-5 text-primary-600 rounded"
                />
                <span>💧 More Irrigation</span>
              </label>
              <label className="flex items-center gap-3 p-3 bg-charcoal-50 rounded-xl cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.scenario_changes.higher_cost}
                  onChange={(e) => setForm({
                    ...form,
                    scenario_changes: { ...form.scenario_changes, higher_cost: e.target.checked }
                  })}
                  className="w-5 h-5 text-primary-600 rounded"
                />
                <span>💰 Higher Cost</span>
              </label>
              <div className="p-3 bg-charcoal-50 rounded-xl">
                <label className="label text-sm">Temperature Change (°C)</label>
                <input
                  type="number"
                  value={form.scenario_changes.temperature_change}
                  onChange={(e) => setForm({
                    ...form,
                    scenario_changes: { ...form.scenario_changes, temperature_change: parseInt(e.target.value) || 0 }
                  })}
                  className="input-field"
                  placeholder="0"
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button type="submit" disabled={creating} className="btn-primary">
                {creating ? <Loader2 className="h-4 w-4 animate-spin inline mr-2" /> : null}
                Create Scenario
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-outline">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Scenarios List */}
      {loading ? (
        <LoadingState title="Loading scenarios..." />
      ) : scenarios.length === 0 ? (
        <EmptyState
          icon="🔮"
          title="No scenarios yet"
          description="Create a what-if scenario to compare different farm conditions"
        />
      ) : (
        <div className="space-y-4">
          {scenarios.map(scenario => (
            <div key={scenario.id} className="card-hover">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-charcoal-900">{scenario.scenario_name}</h3>
                  <p className="text-sm text-charcoal-500 mt-1">{scenario.recommendation}</p>
                </div>
                <div className="text-right">
                  <span className={`text-3xl font-extrabold ${getScoreColor(scenario.overall_score)}`}>
                    {Math.round(scenario.overall_score)}
                  </span>
                  <p className="text-xs text-charcoal-500">Score</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
