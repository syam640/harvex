import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { farmsAPI } from '../services/api';

interface Farm {
  id: number;
  name: string;
  location_name?: string;
  latitude?: number;
  longitude?: number;
  area?: number;
}

interface Field {
  id: number;
  farm_id: number;
  name: string;
  area?: number;
  soil_type?: string;
}

interface CropCycle {
  id: number;
  field_id: number;
  crop_name: string;
  planting_date: string;
  expected_harvest_date?: string;
  status: string;
  predicted_yield?: number;
  predicted_yield_unit?: string;
}

interface AgriculturalSignal {
  level: string;
  reason: string;
}

interface WeatherCurrent {
  temperature: number;
  feels_like: number;
  humidity: number;
  rainfall: number;
  wind_speed: number;
  condition: string;
  description: string;
  observed_at: string;
}

interface WeatherForecastEntry {
  time: string;
  temperature: number;
  humidity: number;
  rain_probability: number;
  rainfall: number;
  wind_speed: number;
  condition: string;
  description: string;
}

interface Weather {
  location?: { name: string; lat: number; lon: number };
  latitude?: number;
  longitude?: number;
  current?: WeatherCurrent;
  forecast?: WeatherForecastEntry[];
  agricultural_signals?: Record<string, AgriculturalSignal>;
  source?: string;
  cached?: boolean;
  cache_age_minutes?: number;
  fetched_at?: string;
}

interface DiseaseResult {
  predicted_disease: string;
  confidence: number;
  severity: string;
}

interface FarmContextType {
  farm: Farm | null;
  field: Field | null;
  cropCycle: CropCycle | null;
  weather: Weather | null;
  diseaseResult: DiseaseResult | null;
  farmLoading: boolean;
  farmError: string | null;
  setFarm: (farm: Farm | null) => void;
  setField: (field: Field | null) => void;
  setCropCycle: (cycle: CropCycle | null) => void;
  setWeather: (weather: Weather | null) => void;
  setDiseaseResult: (result: DiseaseResult | null) => void;
  refreshFarm: () => Promise<void>;
  ensureFarmAndField: () => Promise<{ farm: Farm; field: Field }>;
}

const FarmContext = createContext<FarmContextType | undefined>(undefined);

export function FarmProvider({ children }: { children: ReactNode }) {
  const [farm, setFarm] = useState<Farm | null>(null);
  const [field, setField] = useState<Field | null>(null);
  const [cropCycle, setCropCycle] = useState<CropCycle | null>(null);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [diseaseResult, setDiseaseResult] = useState<DiseaseResult | null>(null);
  const [farmLoading, setFarmLoading] = useState(true);
  const [farmError, setFarmError] = useState<string | null>(null);

  const refreshFarm = useCallback(async () => {
    const token = localStorage.getItem('harvex_token');
    if (!token) {
      setFarmLoading(false);
      return;
    }
    setFarmLoading(true);
    setFarmError(null);
    try {
      const farmsRes = await farmsAPI.getFarms();
      const farms = farmsRes.data;
      if (!farms || farms.length === 0) {
        setFarmLoading(false);
        return;
      }
      const activeFarm = farms[0];
      setFarm(activeFarm);

      const fieldsRes = await farmsAPI.getFields(activeFarm.id);
      const fields = fieldsRes.data;
      if (!fields || fields.length === 0) {
        setFarmLoading(false);
        return;
      }
      const activeField = fields[0];
      setField(activeField);

      const cyclesRes = await farmsAPI.getFieldCropCycles(activeField.id);
      const cycles = cyclesRes.data;
      if (cycles && cycles.length > 0) {
        const activeCycle = cycles.find((c: any) => c.status === 'active') || cycles[0];
        setCropCycle(activeCycle);
      } else {
        setCropCycle(null);
      }
    } catch (err: any) {
      if (err?.response?.status !== 401) {
        setFarmError('Failed to load farm data');
      }
    } finally {
      setFarmLoading(false);
    }
  }, []);

  const ensureFarmAndField = useCallback(async (): Promise<{ farm: Farm; field: Field }> => {
    let currentFarm: Farm = farm!;
    let currentField: Field = field!;

    if (!currentFarm) {
      const res = await farmsAPI.createFarm({ name: 'My Farm' });
      currentFarm = res.data as Farm;
      setFarm(currentFarm);
    }

    if (!currentField) {
      const res = await farmsAPI.createField(currentFarm.id, { name: 'Main Field' });
      currentField = res.data as Field;
      setField(currentField);
    }

    return { farm: currentFarm, field: currentField };
  }, [farm, field]);

  useEffect(() => {
    refreshFarm();
  }, [refreshFarm]);

  return (
    <FarmContext.Provider value={{
      farm, field, cropCycle, weather, diseaseResult,
      farmLoading, farmError,
      setFarm, setField, setCropCycle, setWeather, setDiseaseResult,
      refreshFarm, ensureFarmAndField,
    }}>
      {children}
    </FarmContext.Provider>
  );
}

export const useFarm = () => {
  const context = useContext(FarmContext);
  if (context === undefined) {
    throw new Error('useFarm must be used within a FarmProvider');
  }
  return context;
};
