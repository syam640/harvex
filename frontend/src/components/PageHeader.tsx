import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export default function PageHeader({ title, subtitle, icon, action }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div className="flex items-center gap-3">
        {icon && (
          <div className="w-12 h-12 bg-primary-100 rounded-2xl flex items-center justify-center text-primary-600">
            {icon}
          </div>
        )}
        <div>
          <h1 className="text-3xl font-extrabold text-charcoal-900">{title}</h1>
          {subtitle && <p className="text-charcoal-500 mt-1">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
