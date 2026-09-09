import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { 
  LayoutDashboard, 
  Sprout, 
  Bug, 
  Cloud, 
  Brain, 
  GitCompare, 
  Receipt, 
  Wheat, 
  LineChart, 
  MessageCircle,
  LogOut,
  Globe,
  User,
  Info
} from 'lucide-react';
import BottomNav from '../components/BottomNav';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, labelKey: 'dashboard' },
  { path: '/crop-recommendation', icon: Sprout, labelKey: 'cropRecommendation' },
  { path: '/disease', icon: Bug, labelKey: 'disease' },
  { path: '/weather', icon: Cloud, labelKey: 'weather' },
  { path: '/decisions', icon: Brain, labelKey: 'decisions' },
  { path: '/scenarios', icon: GitCompare, labelKey: 'scenarios' },
  { path: '/expenses', icon: Receipt, labelKey: 'expenses' },
  { path: '/harvest', icon: Wheat, labelKey: 'harvest' },
  { path: '/insights', icon: LineChart, labelKey: 'insights' },
  { path: '/ai-intelligence', icon: Brain, labelKey: 'aiIntelligence' },
  { path: '/assistant', icon: MessageCircle, labelKey: 'assistant' },
  { path: '/profile', icon: User, labelKey: 'profile' },
  { path: '/about', icon: Info, labelKey: 'aboutHarvex' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleLanguage = () => {
    setLanguage(language === 'en' ? 'te' : 'en');
  };

  return (
    <div className="min-h-screen bg-agricultural-gradient">
      {/* Top Navigation - Desktop */}
      <header className="bg-white/80 backdrop-blur-md border-b border-primary-100 fixed top-0 left-0 right-0 z-50 hidden md:block">
        <div className="flex items-center justify-between px-6 py-3 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
              <Sprout className="h-6 w-6 text-white" />
            </div>
            <span className="text-xl font-extrabold text-charcoal-900">HARVEX</span>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={toggleLanguage}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cream-100 hover:bg-cream-200 transition-colors"
            >
              <Globe className="h-4 w-4 text-charcoal-600" />
              <span className="text-sm font-semibold text-charcoal-700">
                {language === 'en' ? 'EN' : 'తె'}
              </span>
            </button>
            
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-charcoal-600">{user?.name}</span>
              <button
                onClick={handleLogout}
                className="p-2 rounded-xl hover:bg-charcoal-100 transition-colors"
                title={t('logout')}
              >
                <LogOut className="h-5 w-5 text-charcoal-500" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Top Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-primary-100 fixed top-0 left-0 right-0 z-50 md:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
              <Sprout className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-extrabold text-charcoal-900">HARVEX</span>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={toggleLanguage}
              className="p-2 rounded-xl bg-cream-100 hover:bg-cream-200 transition-colors"
            >
              <Globe className="h-4 w-4 text-charcoal-600" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl hover:bg-charcoal-100 transition-colors"
            >
              <LogOut className="h-5 w-5 text-charcoal-500" />
            </button>
          </div>
        </div>
      </header>

      <div className="flex pt-14 md:pt-16">
        {/* Desktop Sidebar */}
        <aside className="hidden md:block w-64 bg-white/60 backdrop-blur-sm border-r border-primary-100 fixed left-0 top-16 bottom-0 overflow-y-auto">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200 ${
                    isActive
                      ? 'bg-primary-100 text-primary-700 font-semibold shadow-soft'
                      : 'text-charcoal-600 hover:bg-charcoal-50 hover:text-charcoal-800'
                  }`
                }
              >
                <item.icon className="h-5 w-5" />
                <span className="font-medium">{t(item.labelKey)}</span>
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 md:ml-64 p-4 md:p-8 pb-24 md:pb-8">
          <Outlet />
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <BottomNav />
    </div>
  );
}
