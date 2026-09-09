import { useState, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { locationsAPI } from '../services/api';
import { MapPin } from 'lucide-react';

interface LocationOption {
  id: string;
  name: string;
}

interface LocationSelectorProps {
  onLocationChange: (location: {
    state: string;
    district: string;
    mandal: string;
    town: string;
  }) => void;
  showTown?: boolean;
}

export default function LocationSelector({ onLocationChange, showTown = false }: LocationSelectorProps) {
  const { t, language } = useLanguage();

  const [states, setStates] = useState<LocationOption[]>([]);
  const [districts, setDistricts] = useState<LocationOption[]>([]);
  const [mandals, setMandals] = useState<LocationOption[]>([]);
  const [towns, setTowns] = useState<LocationOption[]>([]);

  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedMandal, setSelectedMandal] = useState('');
  const [selectedTown, setSelectedTown] = useState('');

  const [loading, setLoading] = useState({ states: false, districts: false, mandals: false, towns: false });

  useEffect(() => {
    loadStates();
  }, [language]);

  useEffect(() => {
    if (selectedState) {
      loadDistricts(selectedState);
      setSelectedDistrict('');
      setSelectedMandal('');
      setSelectedTown('');
      setDistricts([]);
      setMandals([]);
      setTowns([]);
    }
  }, [selectedState]);

  useEffect(() => {
    if (selectedState && selectedDistrict) {
      loadMandals(selectedState, selectedDistrict);
      setSelectedMandal('');
      setSelectedTown('');
      setMandals([]);
      setTowns([]);
    }
  }, [selectedDistrict]);

  useEffect(() => {
    if (selectedState && selectedDistrict && selectedMandal) {
      loadTowns(selectedState, selectedDistrict, selectedMandal);
      setSelectedTown('');
      setTowns([]);
    }
  }, [selectedMandal]);

  useEffect(() => {
    onLocationChange({
      state: selectedState,
      district: selectedDistrict,
      mandal: selectedMandal,
      town: selectedTown,
    });
  }, [selectedState, selectedDistrict, selectedMandal, selectedTown]);

  const loadStates = async () => {
    setLoading(prev => ({ ...prev, states: true }));
    try {
      const res = await locationsAPI.getStates(language);
      setStates(res.data);
    } catch (err) {
      console.error('Failed to load states:', err);
    } finally {
      setLoading(prev => ({ ...prev, states: false }));
    }
  };

  const loadDistricts = async (stateId: string) => {
    setLoading(prev => ({ ...prev, districts: true }));
    try {
      const res = await locationsAPI.getDistricts(stateId, language);
      setDistricts(res.data);
    } catch (err) {
      console.error('Failed to load districts:', err);
    } finally {
      setLoading(prev => ({ ...prev, districts: false }));
    }
  };

  const loadMandals = async (stateId: string, districtId: string) => {
    setLoading(prev => ({ ...prev, mandals: true }));
    try {
      const res = await locationsAPI.getMandals(stateId, districtId, language);
      setMandals(res.data);
    } catch (err) {
      console.error('Failed to load mandals:', err);
    } finally {
      setLoading(prev => ({ ...prev, mandals: false }));
    }
  };

  const loadTowns = async (stateId: string, districtId: string, mandalId: string) => {
    setLoading(prev => ({ ...prev, towns: true }));
    try {
      const res = await locationsAPI.getTowns(stateId, districtId, mandalId, language);
      setTowns(res.data);
    } catch (err) {
      console.error('Failed to load towns:', err);
    } finally {
      setLoading(prev => ({ ...prev, towns: false }));
    }
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <MapPin className="h-5 w-5 text-primary-600" />
        <h3 className="text-lg font-semibold text-charcoal-900">{t('selectLocation')}</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">{t('state')}</label>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="input-field"
            disabled={loading.states}
          >
            <option value="">{loading.states ? 'Loading...' : t('selectState')}</option>
            {states.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">{t('district')}</label>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="input-field"
            disabled={!selectedState || loading.districts}
          >
            <option value="">
              {!selectedState ? t('selectStateFirst') : loading.districts ? 'Loading...' : t('selectDistrict')}
            </option>
            {districts.map(d => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">{t('mandal')}</label>
          <select
            value={selectedMandal}
            onChange={(e) => setSelectedMandal(e.target.value)}
            className="input-field"
            disabled={!selectedDistrict || loading.mandals}
          >
            <option value="">
              {!selectedDistrict ? t('selectDistrictFirst') : loading.mandals ? 'Loading...' : t('selectMandal')}
            </option>
            {mandals.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>

        {showTown && (
          <div>
            <label className="label">{t('town')}</label>
            <select
              value={selectedTown}
              onChange={(e) => setSelectedTown(e.target.value)}
              className="input-field"
              disabled={!selectedMandal || loading.towns}
            >
              <option value="">
                {!selectedMandal ? t('selectMandalFirst') : loading.towns ? 'Loading...' : t('selectTown')}
              </option>
              {towns.map(town => (
                <option key={town.id} value={town.id}>{town.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
