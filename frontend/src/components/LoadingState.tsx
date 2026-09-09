import { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  icon?: ReactNode;
  title: string;
  subtitle?: string;
  fullScreen?: boolean;
}

export default function LoadingState({ icon, title, subtitle, fullScreen = false }: LoadingStateProps) {
  const content = (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="mb-6">
        {icon || (
          <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
            <Loader2 className="h-8 w-8 text-primary-600 animate-spin" />
          </div>
        )}
      </div>
      <h3 className="text-xl font-bold text-charcoal-800 mb-2">{title}</h3>
      {subtitle && <p className="text-charcoal-500">{subtitle}</p>}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        {content}
      </div>
    );
  }

  return content;
}
