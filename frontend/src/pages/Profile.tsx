import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { User, Globe, Save, Loader2 } from 'lucide-react';
import PageHeader from '../components/PageHeader';

export default function Profile() {
  const { user, updateUser } = useAuth();
  const { language, setLanguage, t } = useLanguage();

  const [name, setName] = useState(user?.name || '');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');

  const handleSave = async () => {
    setSaving(true);
    setSuccess('');
    try {
      await updateUser({ name });
      setSuccess('Profile updated successfully');
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container max-w-2xl">
      <PageHeader 
        title={t('profile')} 
        subtitle="Manage your account settings"
        icon={<User className="h-6 w-6" />}
      />

      <div className="space-y-6">
        {/* Profile Info */}
        <div className="card">
          <h3 className="font-bold text-charcoal-900 mb-4">Account Information</h3>
          <div className="space-y-4">
            <div>
              <label className="label">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                value={user?.email || ''}
                className="input-field bg-charcoal-50"
                disabled
              />
            </div>
          </div>
        </div>

        {/* Language */}
        <div className="card">
          <h3 className="font-bold text-charcoal-900 mb-4 flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary-600" />
            Language Preference
          </h3>
          <div className="flex gap-3">
            <button
              onClick={() => setLanguage('en')}
              className={`flex-1 p-4 rounded-2xl border-2 transition-all ${
                language === 'en'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-charcoal-200 hover:border-primary-300'
              }`}
            >
              <span className="text-2xl block mb-1">🇺🇸</span>
              <span className="font-bold">English</span>
            </button>
            <button
              onClick={() => setLanguage('te')}
              className={`flex-1 p-4 rounded-2xl border-2 transition-all ${
                language === 'te'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-charcoal-200 hover:border-primary-300'
              }`}
            >
              <span className="text-2xl block mb-1">🇮🇳</span>
              <span className="font-bold">తెలుగు</span>
            </button>
          </div>
        </div>

        {/* Save */}
        {success && (
          <div className="p-4 bg-success-light border border-success/20 rounded-2xl text-success-dark text-sm">
            {success}
          </div>
        )}

        <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
          {saving ? <Loader2 className="h-4 w-4 animate-spin inline mr-2" /> : <Save className="h-4 w-4 inline mr-2" />}
          Save Changes
        </button>
      </div>
    </div>
  );
}
