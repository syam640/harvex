import { useState, useEffect } from 'react';
import { useFarm } from '../contexts/FarmContext';
import { useLanguage } from '../contexts/LanguageContext';
import { expensesAPI, parseApiError } from '../services/api';
import { Receipt, Plus, Trash2, Loader2, IndianRupee, RefreshCw } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';

interface Expense {
  id: number;
  category: string;
  amount: number;
  description: string;
  expense_date: string;
}

const CATEGORIES = [
  { value: 'Seeds', labelEn: 'Seeds', labelTe: 'విత్తనాలు', emoji: '🌱' },
  { value: 'Fertilizer', labelEn: 'Fertilizer', labelTe: 'ఎరువులు', emoji: '🧪' },
  { value: 'Pesticides', labelEn: 'Pesticides', labelTe: 'పురుగుమందులు', emoji: '🐛' },
  { value: 'Labour', labelEn: 'Labour', labelTe: 'శ్రమ', emoji: '👷' },
  { value: 'Irrigation', labelEn: 'Irrigation', labelTe: 'నీటిపారుదల', emoji: '💧' },
  { value: 'Transport', labelEn: 'Transport', labelTe: 'రవాణా', emoji: '🚛' },
  { value: 'Equipment', labelEn: 'Equipment', labelTe: 'పరికరాలు', emoji: '🚜' },
  { value: 'Other', labelEn: 'Other', labelTe: 'ఇతర', emoji: '📦' },
];

export default function Expenses() {
  const { cropCycle } = useFarm();
  const { t, language } = useLanguage();

  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    category: 'Seeds',
    amount: '',
    description: '',
    date: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    if (cropCycle) {
      loadExpenses();
    } else {
      setLoading(false);
    }
  }, [cropCycle]);

  const loadExpenses = async () => {
    if (!cropCycle) return;
    setLoading(true);
    setError('');
    try {
      const res = await expensesAPI.getExpenses(cropCycle.id);
      setExpenses(res.data || []);
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
      await expensesAPI.createExpense(cropCycle.id, {
        category: form.category,
        amount: parseFloat(form.amount),
        description: form.description || null,
        expense_date: form.date ? `${form.date}T00:00:00` : new Date().toISOString(),
      });
      setShowForm(false);
      setForm({ category: 'Seeds', amount: '', description: '', date: new Date().toISOString().split('T')[0] });
      loadExpenses();
    } catch (err: any) {
      setError(parseApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (expenseId: number) => {
    if (!cropCycle || !confirm(language === 'te' ? 'ఈ ఖర్చును తొలగించాలా?' : 'Delete this expense?')) return;
    try {
      await expensesAPI.deleteExpense(cropCycle.id, expenseId);
      loadExpenses();
    } catch (err) {
      console.error(err);
    }
  };

  const totalExpenses = expenses.reduce((sum, e) => sum + (e.amount || 0), 0);

  const getCategoryLabel = (cat: string) => {
    const found = CATEGORIES.find(c => c.value === cat);
    if (!found) return cat;
    return language === 'te' ? found.labelTe : found.labelEn;
  };

  const getCategoryEmoji = (cat: string) => {
    return CATEGORIES.find(c => c.value === cat)?.emoji || '📦';
  };

  if (loading) return <LoadingState title={t('loadingExpenses') || 'Loading expenses...'} />;

  return (
    <div className="page-container">
      <PageHeader
        title={t('expenses') || 'Farm Expenses'}
        subtitle={t('trackCosts') || 'Track all your cultivation costs'}
        icon={<Receipt className="h-6 w-6" />}
        action={
          cropCycle && (
            <button onClick={() => setShowForm(!showForm)} className="btn-primary">
              <Plus className="h-4 w-4 inline mr-2" />
              {t('addExpense') || 'Add Expense'}
            </button>
          )
        }
      />

      {!cropCycle ? (
        <EmptyState
          icon="🌾"
          title={t('noActiveCrop') || 'No active crop'}
          description={t('startCropToTrack') || 'Start a crop to track expenses'}
          action={
            <button onClick={() => window.location.href = '/crop-recommendation-intelligent'} className="btn-primary">
              {t('getCropRecommendation') || 'Get Crop Recommendation'}
            </button>
          }
        />
      ) : error && expenses.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-danger-dark mb-4">{error}</p>
          <button onClick={loadExpenses} className="btn-primary">
            <RefreshCw className="h-4 w-4 inline mr-2" />
            {t('tryAgain') || 'Try Again'}
          </button>
        </div>
      ) : expenses.length === 0 && !showForm ? (
        <EmptyState
          icon="💰"
          title={t('noExpensesRecorded') || 'No expenses recorded yet'}
          description={t('startTrackingCosts') || 'Start tracking your cultivation costs'}
          action={
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <Plus className="h-4 w-4 inline mr-2" />
              {t('addFirstExpense') || 'Add First Expense'}
            </button>
          }
        />
      ) : (
        <>
          <div className="card bg-gradient-to-r from-harvest-50 to-harvest-100 border-harvest-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-harvest-200 rounded-2xl flex items-center justify-center">
                  <IndianRupee className="h-6 w-6 text-harvest-700" />
                </div>
                <div>
                  <p className="text-sm text-charcoal-500">{t('totalExpenses') || 'Total Expenses'}</p>
                  <p className="text-3xl font-extrabold text-charcoal-900">₹{totalExpenses.toLocaleString()}</p>
                </div>
              </div>
              <p className="text-sm text-charcoal-500">{expenses.length} {language === 'te' ? 'లావాదేవీలు' : 'transactions'}</p>
            </div>
          </div>

          {error && (
            <div className="bg-danger-light border border-danger/20 rounded-xl p-3 text-sm text-danger-dark">
              {error}
            </div>
          )}

          {showForm && (
            <div className="card animate-slide-up">
              <h3 className="font-bold text-charcoal-900 mb-4">{t('addExpense') || 'Add Expense'}</h3>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="label">{t('category') || 'Category'}</label>
                  <div className="grid grid-cols-4 gap-2">
                    {CATEGORIES.map(cat => (
                      <button
                        key={cat.value}
                        type="button"
                        onClick={() => setForm({ ...form, category: cat.value })}
                        className={`p-3 rounded-xl border-2 text-center transition-all ${
                          form.category === cat.value
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-charcoal-200 hover:border-primary-300'
                        }`}
                      >
                        <span className="text-xl">{cat.emoji}</span>
                        <p className="text-xs mt-1">{language === 'te' ? cat.labelTe : cat.labelEn}</p>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">{t('amount') || 'Amount'} (₹)</label>
                    <input
                      type="number"
                      value={form.amount}
                      onChange={(e) => setForm({ ...form, amount: e.target.value })}
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
                <div>
                  <label className="label">{t('description') || 'Description'} ({language === 'te' ? 'ఐచ్ఛికం' : 'optional'})</label>
                  <input
                    type="text"
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="input-field"
                    placeholder={language === 'te' ? 'ఈ ఖర్చు ఏమిటి?' : 'What was this expense for?'}
                  />
                </div>
                <div className="flex gap-3">
                  <button type="submit" disabled={submitting} className="btn-primary">
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin inline mr-2" /> : null}
                    {t('saveExpense') || 'Save Expense'}
                  </button>
                  <button type="button" onClick={() => setShowForm(false)} className="btn-outline">
                    {t('cancel') || 'Cancel'}
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="space-y-3">
            {expenses.map(expense => (
              <div key={expense.id} className="card flex items-center gap-4">
                <span className="text-3xl">{getCategoryEmoji(expense.category)}</span>
                <div className="flex-1">
                  <p className="font-bold text-charcoal-900">{getCategoryLabel(expense.category)}</p>
                  {expense.description && (
                    <p className="text-sm text-charcoal-500">{expense.description}</p>
                  )}
                  <p className="text-xs text-charcoal-400 mt-1">{expense.expense_date?.split('T')[0] || ''}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-extrabold text-charcoal-900">₹{expense.amount.toLocaleString()}</p>
                  <button
                    onClick={() => handleDelete(expense.id)}
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
