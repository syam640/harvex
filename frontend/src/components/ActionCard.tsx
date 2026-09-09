import { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

interface ActionCardProps {
  icon: ReactNode;
  title: string;
  description?: string;
  path: string;
  color?: string;
}

export default function ActionCard({ icon, title, description, path, color = 'bg-primary-100 text-primary-700' }: ActionCardProps) {
  const navigate = useNavigate();
  
  return (
    <button
      onClick={() => navigate(path)}
      className="card-hover text-left w-full group"
    >
      <div className={`w-14 h-14 ${color} rounded-2xl flex items-center justify-center mb-3 
                       group-hover:scale-110 transition-transform duration-200`}>
        {icon}
      </div>
      <h3 className="font-bold text-charcoal-800 group-hover:text-primary-600 transition-colors">
        {title}
      </h3>
      {description && <p className="text-sm text-charcoal-500 mt-1">{description}</p>}
    </button>
  );
}
