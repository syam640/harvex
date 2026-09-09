import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { FarmProvider } from './contexts/FarmContext';
import { LanguageProvider } from './contexts/LanguageContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import CropRecommendation from './pages/CropRecommendation';
import IntelligentCropRecommendation from './pages/IntelligentCropRecommendation';
import Disease from './pages/Disease';
import Weather from './pages/Weather';
import Decisions from './pages/Decisions';
import Scenarios from './pages/Scenarios';
import Expenses from './pages/Expenses';
import Harvest from './pages/Harvest';
import Insights from './pages/Insights';
import Assistant from './pages/Assistant';
import AIIntelligence from './pages/AIIntelligence';
import Profile from './pages/Profile';
import About from './pages/About';
import Layout from './layouts/Layout';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }
  
  return user ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <AuthProvider>
      <LanguageProvider>
        <FarmProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/" element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }>
                <Route index element={<Dashboard />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="crop-recommendation" element={<CropRecommendation />} />
                <Route path="crop-recommendation-intelligent" element={<IntelligentCropRecommendation />} />
                <Route path="disease" element={<Disease />} />
                <Route path="weather" element={<Weather />} />
                <Route path="decisions" element={<Decisions />} />
                <Route path="scenarios" element={<Scenarios />} />
                <Route path="expenses" element={<Expenses />} />
                <Route path="harvest" element={<Harvest />} />
                <Route path="insights" element={<Insights />} />
                <Route path="assistant" element={<Assistant />} />
                <Route path="ai-intelligence" element={<AIIntelligence />} />
                <Route path="profile" element={<Profile />} />
                <Route path="about" element={<About />} />
              </Route>
            </Routes>
          </Router>
        </FarmProvider>
      </LanguageProvider>
    </AuthProvider>
  );
}

export default App;
