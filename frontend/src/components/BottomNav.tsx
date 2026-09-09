import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Sprout, Bug, MessageCircle, MoreHorizontal } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, labelKey: 'home' },
  { path: '/crop-recommendation', icon: Sprout, labelKey: 'crops' },
  { path: '/disease', icon: Bug, labelKey: 'health' },
  { path: '/assistant', icon: MessageCircle, labelKey: 'assistant' },
  { path: '/about', icon: MoreHorizontal, labelKey: 'more' },
];

export default function BottomNav() {
  const { t } = useLanguage();
  
  return (
    <nav className="bottom-nav">
      <div className="flex items-center justify-around py-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `bottom-nav-item ${isActive ? 'active' : ''}`
            }
          >
            <item.icon className="h-6 w-6" />
            <span className="text-xs mt-1 font-medium">{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
