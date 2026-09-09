import { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="card text-center py-12 px-6">
      <div className="w-20 h-20 mx-auto mb-4 bg-cream-100 rounded-full flex items-center justify-center text-4xl animate-bounce-gentle">
        {icon}
      </div>
      <h3 className="text-xl font-bold text-charcoal-800 mb-2">{title}</h3>
      <p className="text-charcoal-500 mb-6 max-w-sm mx-auto">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
