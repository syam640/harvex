import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('harvex_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('harvex_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export function parseApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data) {
      if (typeof data === 'string') return data;
      if (data.detail) {
        if (typeof data.detail === 'string') return data.detail;
        if (Array.isArray(data.detail)) {
          return data.detail.map((d: any) => d.msg || d).join('; ');
        }
        return JSON.stringify(data.detail);
      }
      if (data.message) return data.message;
    }
    if (error.message) return error.message;
    return 'An unexpected error occurred';
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred';
}

export const authAPI = {
  register: (data: { name: string; email: string; password: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
  updateMe: (data: { name?: string; preferred_language?: string }) =>
    api.put('/auth/me', data),
};

export const farmsAPI = {
  getFarms: () => api.get('/farms'),
  createFarm: (data: any) => api.post('/farms', data),
  getFields: (farmId: number) => api.get(`/farms/${farmId}/fields`),
  createField: (farmId: number, data: any) => api.post(`/farms/${farmId}/fields`, data),
  createCropCycle: (data: any) => api.post('/crop-cycles', data),
  getCropCycle: (cycleId: number) => api.get(`/crop-cycles/${cycleId}`),
  getFieldCropCycles: (fieldId: number) => api.get(`/fields/${fieldId}/crop-cycles`),
  updateFarmLocation: (lat: number, lon: number, locationName?: string) =>
    api.patch('/farms/location', { latitude: lat, longitude: lon, location_name: locationName }),
};

export const cropAPI = {
  recommend: (data: any) => api.post('/crop/recommend', data),
  getAll: () => api.get('/crop/all'),
  getCategories: () => api.get('/crop/categories'),
};

export const intelligentCropAPI = {
  recommend: (data: {
    latitude: number;
    longitude: number;
    location_name?: string;
    location_source?: string;
    season: string;
    water_availability: string;
    irrigation_method: string;
    soil_report?: {
      ph?: number;
      nitrogen?: number;
      phosphorus?: number;
      potassium?: number;
      soil_type?: string;
      organic_carbon?: number;
    };
  }) => api.post('/crop-recommendations', data),
  getCatalog: () => api.get('/crop-recommendations/catalog'),
  getCropDetail: (cropId: string) => api.get(`/crop-recommendations/catalog/${cropId}`),
  getCategories: () => api.get('/crop-recommendations/categories'),
};

export const diseaseAPI = {
  scan: (formData: FormData) =>
    api.post('/disease/scan', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getHistory: (cropCycleId: number) =>
    api.get(`/disease/history/${cropCycleId}`),
  getTimeline: (cropCycleId: number) =>
    api.get(`/disease/timeline/${cropCycleId}`),
  getScanDetail: (scanId: number) =>
    api.get(`/disease/scans/${scanId}`),
  compareScans: (scanId: number) =>
    api.get(`/disease/compare/${scanId}`),
};

export const weatherAPI = {
  getCurrent: (lat: number, lon: number) =>
    api.get('/weather/current', { params: { lat, lon } }),
  getForecast: (lat: number, lon: number) =>
    api.get('/weather/forecast', { params: { lat, lon } }),
  geocode: (city: string) =>
    api.post('/weather/geocode', { city }),
  setFarmLocation: (lat: number, lon: number) =>
    api.post('/weather/set-farm-location', null, { params: { lat, lon } }),
};

export const decisionAPI = {
  analyze: (data: { crop_cycle_id: number }) =>
    api.post('/decision/analyze', data),
};

export const expensesAPI = {
  getExpenses: (cycleId: number) => api.get(`/crop-cycles/${cycleId}/expenses`),
  createExpense: (cycleId: number, data: any) =>
    api.post(`/crop-cycles/${cycleId}/expenses`, data),
  updateExpense: (cycleId: number, expenseId: number, data: any) =>
    api.put(`/crop-cycles/${cycleId}/expenses/${expenseId}`, data),
  deleteExpense: (cycleId: number, expenseId: number) =>
    api.delete(`/crop-cycles/${cycleId}/expenses/${expenseId}`),
};

export const harvestAPI = {
  getHarvests: (cycleId: number) => api.get(`/crop-cycles/${cycleId}/harvests`),
  createHarvest: (cycleId: number, data: any) =>
    api.post(`/crop-cycles/${cycleId}/harvests`, data),
  updateHarvest: (cycleId: number, harvestId: number, data: any) =>
    api.put(`/crop-cycles/${cycleId}/harvests/${harvestId}`, data),
  deleteHarvest: (cycleId: number, harvestId: number) =>
    api.delete(`/crop-cycles/${cycleId}/harvests/${harvestId}`),
};

export const insightsAPI = {
  getPredictionVsReality: (cycleId: number) =>
    api.get(`/crop-cycles/${cycleId}/prediction-vs-reality`),
};

export const scenariosAPI = {
  getScenarios: (cycleId: number) => api.get(`/scenarios/${cycleId}`),
  createScenario: (data: any) => api.post('/scenarios', data),
};

export const assistantAPI = {
  chat: (data: { question: string; language: string }) =>
    api.post('/assistant/chat', data),
};

export const aiAPI = {
  getStatus: () => api.get('/ai/status'),
  getCropRecommendation: () => api.post('/ai/crop-recommendation'),
  getLocationCropRecommendation: (params: {
    state_id: string;
    district_id: string;
    mandal_id?: string;
    season?: string;
    soil_type?: string;
  }) => api.post('/ai/location-crop-recommendation', null, { params }),
  getTreatment: (cropName: string, disease: string, severity: string = 'medium') =>
    api.post(`/ai/treatment?crop_name=${cropName}&disease=${encodeURIComponent(disease)}&severity=${severity}`),
  getRisk: () => api.post('/ai/risk'),
  getIrrigation: () => api.post('/ai/irrigation'),
  getFinancial: () => api.post('/ai/financial'),
  getInsights: () => api.post('/ai/insights'),
  getWhatIf: (scenarioChanges: any) => api.post('/ai/what-if', scenarioChanges),
  getDiseaseAnalysis: (formData: FormData) =>
    api.post('/ai/disease-analysis', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

export const locationsAPI = {
  getStates: (lang: string = 'en') => api.get('/locations/states', { params: { lang } }),
  getDistricts: (stateId: string, lang: string = 'en') =>
    api.get(`/locations/states/${stateId}/districts`, { params: { lang } }),
  getMandals: (stateId: string, districtId: string, lang: string = 'en') =>
    api.get(`/locations/states/${stateId}/districts/${districtId}/mandals`, { params: { lang } }),
  getTowns: (stateId: string, districtId: string, mandalId: string, lang: string = 'en') =>
    api.get(`/locations/states/${stateId}/districts/${districtId}/mandals/${mandalId}/towns`, { params: { lang } }),
  getLocationContext: (stateId: string, districtId: string) =>
    api.get(`/locations/states/${stateId}/districts/${districtId}/context`),
};

export default api;
