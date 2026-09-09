import { Calendar, MapPin } from 'lucide-react';

interface CropCardProps {
  cropName: string;
  status: string;
  daysActive?: number;
  location?: string;
  health?: 'healthy' | 'warning' | 'danger';
  onClick?: () => void;
}

const healthColors = {
  healthy: 'bg-success-light text-success-dark',
  warning: 'bg-warning-light text-warning-dark',
  danger: 'bg-danger-light text-danger-dark',
};

const getCropEmoji = (crop: string) => {
  const c = crop.toLowerCase();
  if (c.includes('tomato') || c.includes('tom')) return '🍅';
  if (c.includes('rice') || c.includes('paddy')) return '🌾';
  if (c.includes('maize') || c.includes('corn')) return '🌽';
  if (c.includes('cotton')) return '🤍';
  if (c.includes('chilli') || c.includes('chili')) return '🌶️';
  if (c.includes('onion')) return '🧅';
  if (c.includes('potato')) return '🥔';
  if (c.includes('brinjal') || c.includes('eggplant')) return '🍆';
  if (c.includes('mango')) return '🥭';
  if (c.includes('banana')) return '🍌';
  if (c.includes('groundnut') || c.includes('peanut')) return '🥜';
  if (c.includes('wheat')) return '🌾';
  if (c.includes('sugarcane')) return '🎋';
  if (c.includes('coconut')) return '🥥';
  return '🌱';
};

export default function CropCard({ cropName, status, daysActive, location, health = 'healthy', onClick }: CropCardProps) {
  return (
    <div 
      onClick={onClick}
      className={`card-hover ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-start gap-4">
        <div className="text-5xl">{getCropEmoji(cropName)}</div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-charcoal-900 text-lg">{cropName}</h3>
            <span className={`badge ${healthColors[health]}`}>{status}</span>
          </div>
          {daysActive !== undefined && (
            <div className="flex items-center gap-2 mt-2 text-sm text-charcoal-500">
              <Calendar className="h-4 w-4" />
              <span>Day {daysActive}</span>
            </div>
          )}
          {location && (
            <div className="flex items-center gap-2 mt-1 text-sm text-charcoal-500">
              <MapPin className="h-4 w-4" />
              <span>{location}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
