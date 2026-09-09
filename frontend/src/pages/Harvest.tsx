import { useState, useEffect } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { useLanguage } from '../contexts/LanguageContext';
import { harvestAPI, parseApiError } from '../services/api';
import { Wheat, Plus, Trash2, Loader2, IndianRupee, RefreshCw } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';

interface Harvest {
  id: number;
  quantity: number;
  unit: string;
  selling_price: number;
  buyer: string;
  market: string;
  harvest_date: string;
}

const UNITS = [
  { value: 'kg', labelEn: 'kg', labelTe: 'కిలో' },
  { value: 'quintal', labelEn: 'quintal', labelTe: 'క్వింటాల్' },
  { value: 'ton', labelEn: 'ton', labelTe: 'టన్ను' },
  { value: 'pieces', labelEn: 'pieces', labelTe: 'ముక్కలు' },
];

export default function Harvest() {
  const { cropCycle } = useFarm();
  const { t, language } = useLanguage();

  const [harvests, setHarvests] = useState<Harvest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    quantity: '',
    unit: 'kg',
    selling_price: '',
    buyer: '',
    market: '',
    date: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    if (cropCycle) {
      loadHarvests();
    } else {
      setLoading(false);
    }
  }, [cropCycle]);

  const loadHarvests = async () => {
    if (!cropCycle) return;
    setLoading(true);
    setError('');
    try {
      const res = await harvestAPI.getHarvests(cropCycle.id);
      setHarvests(res.data || []);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cropCycle) return;
    setSubmitting(true);
    setError('');
    try {
      await harvestAPI.createHarvest(cropCycle.id, {
        harvest_date: form.date ? `${form.date}T00:00:00` : new Date().toISOString(),
        quantity: parseFloat(form.quantity),
        unit: form.unit,
        selling_price: parseFloat(form.selling_price),
        buyer: form.buyer || null,
        market: form.market || null,
      });
      setShowForm(false);
      setForm({ quantity: '', unit: 'kg', selling_price: '', buyer: '', market: '', date: new Date().toISOString().split('T')[0] });
      loadHarvests();
    } catch (err: any) {
      setError(parseApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (harvestId: number) => {
    if (!cropCycle || !confirm(language === 'te' ? 'ఈ కోత రికార్డును తొలగించాలా?' : 'Delete this harvest record?')) return;
    try {
      await harvestAPI.deleteHarvest(cropCycle.id, harvestId);
      loadHarvests();
    } catch (err) {
      console.error(err);
    }
  };

  const totalQuantity = harvests.reduce((sum, h) => sum + (h.quantity || 0), 0);
  const totalRevenue = harvests.reduce((sum, h) => sum + ((h.quantity || 0) * (h.selling_price || 0)), 0);

  if (loading) return <LoadingState title={t('loadingHarvests') || 'Loading harvest records...'} />;

  return (
    <div className="page-container">
      <PageHeader
        title={t('harvest') || 'Harvest & Yield'}
        subtitle={t('trackHarvest') || 'Track your harvest and revenue'}
        icon={<Wheat className="h-6 w-6" />}
        action={
          cropCycle && (
            <button onClick={() => setShowForm(!showForm)} className="btn-primary">
              <Plus className="h-4 w-4 inline mr-2" />
              {t('recordHarvest') || 'Add Harvest'}
            </button>
          )
        }
      />

      {!cropCycle ? (
        <EmptyState
          icon="🌾"
          title={t('noActiveCrop') || 'No active crop'}
          description={t('startCropToRecord') || 'Start a crop to record harvests'}
          action={
            <button onClick={() => window.location.href = '/crop-recommendation-intelligent'} className="btn-primary">
              {t('getCropRecommendation') || 'Get Crop Recommendation'}
            </button>
          }
        />
      ) : error && harvests.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-danger-dark mb-4">{error}</p>
          <button onClick={loadHarvests} className="btn-primary">
            <RefreshCw className="h-4 w-4 inline mr-2" />
            {t('tryAgain') || 'Try Again'}
          </button>
        </div>
      ) : harvests.length === 0 && !showForm ? (
        <EmptyState
          icon="🌾"
          title={t('noHarvestRecorded') || 'No harvest recorded yet'}
          description={t('recordFirstHarvest') || 'Record your first harvest to see profitability'}
          action={
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <Plus className="h-4 w-4 inline mr-2" />
              {t('recordFirstHarvest') || 'Record First Harvest'}
            </button>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card bg-gradient-to-r from-primary-50 to-primary-100 border-primary-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-primary-200 rounded-2xl flex items-center justify-center">
                  <Wheat className="h-6 w-6 text-primary-700" />
                </div>
                <div>
                  <p className="text-sm text-charcoal-500">{t('totalHarvest') || 'Total Harvest'}</p>
                  <p className="text-3xl font-extrabold text-charcoal-900">{totalQuantity} kg</p>
                </div>
              </div>
            </div>
            <div className="card bg-gradient-to-r from-success-light to-success-light/50 border-success/20">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-success/20 rounded-2xl flex items-center justify-center">
                  <IndianRupee className="h-6 w-6 text-success-dark" />
                </div>
                <div>
                  <p className="text-sm text-charcoal-500">{t('revenue') || 'Total Revenue'}</p>
                  <p className="text-3xl font-extrabold text-charcoal-900">₹{totalRevenue.toLocaleString()}</p>
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-danger-light border border-danger/20 rounded-xl p-3 text-sm text-danger-dark">
              {error}
            </div>
          )}

          {showForm && (
            <div className="card animate-slide-up">
              <h3 className="font-bold text-charcoal-900 mb-4">{t('recordHarvest') || 'Record Harvest'}</h3>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">{t('quantity') || 'Quantity'}</label>
                    <input
                      type="number"
                      value={form.quantity}
                      onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                      className="input-field"
                      placeholder="0"
                      required
                    />
                  </div>
                  <div>
                    <label className="label">{t('unit') || 'Unit'}</label>
                    <select
                      value={form.unit}
                      onChange={(e) => setForm({ ...form, unit: e.target.value })}
                      className="input-field"
                    >
                      {UNITS.map(u => (
                        <option key={u.value} value={u.value}>
                          {language === 'te' ? u.labelTe : u.labelEn}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">{t('sellingPrice') || 'Selling Price'} (₹/{language === 'te' ? 'కిలో' : 'kg'})</label>
                    <input
                      type="number"
                      value={form.selling_price}
                      onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
                      className="input-field"
                      placeholder="0"
                      required
                    />
                  </div>
                  <div>
                    <label className="label">{t('date') || 'Date'}</label>
                    <input
                      type="date"
                      value={form.date}
                      onChange={(e) => setForm({ ...form, date: e.target.value })}
                      className="input-field"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">{t('buyer') || 'Buyer'} ({language === 'te' ? 'ఐచ్ఛికం' : 'optional'})</label>
                    <input
                      type="text"
                      value={form.buyer}
                      onChange={(e) => setForm({ ...form, buyer: e.target.value })}
                      className="input-field"
                      placeholder={language === 'te' ? 'కొనుగోలుదారు పేరు' : 'Buyer name'}
                    />
                  </div>
                  <div>
                    <label className="label">{t('market') || 'Market'} ({language === 'te' ? 'ఐచ్ఛికం' : 'optional'})</label>
                    <input
                      type="text"
                      value={form.market}
                      onChange={(e) => setForm({ ...form, market: e.target.value })}
                      className="input-field"
                      placeholder={language === 'te' ? 'మార్కెట్ పేరు' : 'Market name'}
                    />
                  </div>
                </div>
                <div className="flex gap-3">
                  <button type="submit" disabled={submitting} className="btn-primary">
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin inline mr-2" /> : null}
                    {t('saveHarvest') || 'Save Harvest'}
                  </button>
                  <button type="button" onClick={() => setShowForm(false)} className="btn-outline">
                    {t('cancel') || 'Cancel'}
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="space-y-3">
            {harvests.map(harvest => (
              <div key={harvest.id} className="card flex items-center gap-4">
                <span className="text-3xl">🌾</span>
                <div className="flex-1">
                  <p className="font-bold text-charcoal-900">{harvest.quantity} {harvest.unit}</p>
                  <p className="text-sm text-charcoal-500">
                    ₹{harvest.selling_price}/{harvest.unit}
                    {harvest.buyer && ` • ${harvest.buyer}`}
                  </p>
                  <p className="text-xs text-charcoal-400 mt-1">{harvest.harvest_date?.split('T')[0] || ''}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-extrabold text-success-dark">
                    ₹{((harvest.quantity || 0) * (harvest.selling_price || 0)).toLocaleString()}
                  </p>
                  <button
                    onClick={() => handleDelete(harvest.id)}
                    className="text-danger hover:text-danger-dark mt-1"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
