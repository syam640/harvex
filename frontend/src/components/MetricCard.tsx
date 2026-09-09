import { ReactNode } from 'react';

interface MetricCardProps {
  icon: ReactNode;
  label: string;
  value: string | number;
  unit?: string;
  color?: 'green' | 'blue' | 'amber' | 'red' | 'purple';
  size?: 'sm' | 'md' | 'lg';
}

const colorMap = {
  green: 'bg-primary-100 text-primary-700',
  blue: 'bg-sky-100 text-sky-700',
  amber: 'bg-harvest-100 text-harvest-700',
  red: 'bg-danger-light text-danger-dark',
  purple: 'bg-purple-100 text-purple-700',
};

export default function MetricCard({ icon, label, value, unit, color = 'green', size = 'md' }: MetricCardProps) {
  return (
    <div className={`card ${size === 'lg' ? 'p-6' : 'p-4'}`}>
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorMap[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-sm text-charcoal-500">{label}</p>
          <p className={`font-extrabold text-charcoal-900 ${size === 'lg' ? 'text-3xl' : 'text-xl'}`}>
            {value}{unit && <span className="text-sm font-medium text-charcoal-500 ml-1">{unit}</span>}
          </p>
        </div>
      </div>
    </div>
  );
}
