import { Sprout, Brain, Cloud, BarChart3, Shield, Globe, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function About() {
  const navigate = useNavigate();

  const features = [
    { icon: Brain, title: 'AI-Powered Insights', description: 'NVIDIA NIM-powered artificial intelligence for crop recommendations, disease detection, and farm management decisions.', color: 'bg-purple-100 text-purple-700' },
    { icon: Sprout, title: 'Location-Based Recommendations', description: 'Smart crop suggestions based on your State, District, and Mandal location with agro-climatic zone awareness.', color: 'bg-primary-100 text-primary-700' },
    { icon: Cloud, title: 'Weather Intelligence', description: 'Real-time weather data with AI-driven irrigation scheduling and risk analysis for your farm.', color: 'bg-sky-100 text-sky-700' },
    { icon: BarChart3, title: 'Decision Analytics', description: 'Data-driven farming decisions with expense tracking, harvest management, and financial insights.', color: 'bg-harvest-100 text-harvest-700' },
    { icon: Shield, title: 'Disease Detection', description: 'Upload leaf images for AI-powered disease identification supporting 15+ crops.', color: 'bg-danger-light text-danger-dark' },
    { icon: Globe, title: 'Multilingual Support', description: 'Available in English and Telugu to serve farmers in their preferred language.', color: 'bg-cream-200 text-earth-700' },
  ];

  const steps = [
    { icon: '📍', title: 'Farm Location', description: 'Select your State, District, and Mandal' },
    { icon: '🌾', title: 'Crop Recommendation', description: 'Get AI-powered crop suggestions' },
    { icon: '🚜', title: 'Start Farm', description: 'Begin your farming cycle' },
    { icon: '🌱', title: 'Manage Crop', description: 'Monitor health, weather, and decisions' },
    { icon: '📊', title: 'Harvest & Insights', description: 'Track outcomes and learn' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-16 pb-24">
      {/* Hero Section */}
      <div className="text-center space-y-6 pt-8">
        <div className="inline-flex items-center justify-center w-24 h-24 bg-primary-500 rounded-3xl shadow-glow mb-4">
          <Sprout className="h-12 w-12 text-white" />
        </div>
        <h1 className="text-5xl font-extrabold text-charcoal-900">
          About <span className="text-gradient-green">HARVEX</span>
        </h1>
        <p className="text-xl text-charcoal-600 max-w-3xl mx-auto leading-relaxed">
          Smarter Farms. Better Decisions.
        </p>
        <p className="text-charcoal-500 max-w-2xl mx-auto">
          HARVEX is an AI-powered Farm Decision Intelligence Platform that connects farm conditions, 
          AI analysis, crop health, weather, decisions and actual farm outcomes.
        </p>
      </div>

      {/* How HARVEX Works */}
      <div>
        <h2 className="text-3xl font-extrabold text-charcoal-900 text-center mb-8">How HARVEX Works</h2>
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {steps.map((step, i) => (
            <div key={i} className="flex-1 text-center">
              <div className="w-20 h-20 mx-auto bg-primary-100 rounded-3xl flex items-center justify-center text-4xl mb-3">
                {step.icon}
              </div>
              <h3 className="font-bold text-charcoal-900">{step.title}</h3>
              <p className="text-sm text-charcoal-500 mt-1">{step.description}</p>
              {i < steps.length - 1 && (
                <ArrowRight className="h-6 w-6 text-primary-400 mx-auto mt-4 hidden md:block" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* AI Intelligence */}
      <div className="card bg-gradient-to-br from-primary-50 to-sky-50 border-primary-200">
        <h2 className="text-2xl font-extrabold text-charcoal-900 mb-6 text-center">AI Intelligence</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { icon: '🌾', title: 'Crop Recommendation' },
            { icon: '📷', title: 'Disease Detection' },
            { icon: '💊', title: 'Treatment Guidance' },
            { icon: '⚠️', title: 'Risk Analysis' },
            { icon: '💧', title: 'Irrigation Advice' },
            { icon: '🧠', title: 'Decision Engine' },
            { icon: '🔮', title: 'What-If Scenarios' },
            { icon: '💬', title: 'AI Assistant' },
            { icon: '📊', title: 'Financial Insights' },
          ].map((item, i) => (
            <div key={i} className="bg-white/70 rounded-2xl p-4 text-center">
              <span className="text-3xl block mb-2">{item.icon}</span>
              <p className="font-bold text-charcoal-800 text-sm">{item.title}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Key Features */}
      <div>
        <h2 className="text-3xl font-extrabold text-charcoal-900 text-center mb-8">Key Features</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <div key={i} className="card-hover">
              <div className={`w-14 h-14 ${feature.color} rounded-2xl flex items-center justify-center mb-4`}>
                <feature.icon className="h-7 w-7" />
              </div>
              <h3 className="text-lg font-bold text-charcoal-900 mb-2">{feature.title}</h3>
              <p className="text-charcoal-600 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Technology */}
      <div className="card">
        <h2 className="text-2xl font-extrabold text-charcoal-900 mb-6 text-center">Technology Stack</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: '⚛️', name: 'React + TypeScript' },
            { icon: '⚡', name: 'FastAPI Backend' },
            { icon: '🤖', name: 'NVIDIA NIM AI' },
            { icon: '🌤️', name: 'OpenWeather API' },
            { icon: '🗄️', name: 'SQLite Database' },
            { icon: '🔐', name: 'JWT Authentication' },
            { icon: '🌐', name: 'Multilingual i18n' },
            { icon: '🎨', name: 'Tailwind CSS' },
          ].map((tech, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-charcoal-50 rounded-xl">
              <span className="text-2xl">{tech.icon}</span>
              <span className="text-sm font-medium text-charcoal-700">{tech.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="text-center space-y-6">
        <h2 className="text-3xl font-extrabold text-charcoal-900">From Farm Conditions to Better Decisions</h2>
        <p className="text-charcoal-500">Helping farmers make smarter decisions throughout the crop lifecycle.</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button onClick={() => navigate('/dashboard')} className="btn-primary btn-pill text-lg px-8">
            Explore Dashboard
          </button>
          <button onClick={() => navigate('/ai-intelligence')} className="btn-secondary btn-pill text-lg px-8">
            Try AI Intelligence
          </button>
        </div>
      </div>
    </div>
  );
}
