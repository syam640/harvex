import { Cloud, Droplets, Wind } from 'lucide-react';

interface WeatherCardProps {
  temperature: number;
  condition: string;
  humidity: number;
  rainfall: number;
  windSpeed: number;
  location?: string;
  compact?: boolean;
}

const getWeatherEmoji = (condition: string) => {
  const c = condition.toLowerCase();
  if (c.includes('clear') || c.includes('sunny')) return '☀️';
  if (c.includes('cloud') && c.includes('part')) return '⛅';
  if (c.includes('cloud')) return '☁️';
  if (c.includes('rain') || c.includes('drizzle')) return '🌧️';
  if (c.includes('storm') || c.includes('thunder')) return '⛈️';
  if (c.includes('fog') || c.includes('mist')) return '🌫️';
  return '🌤️';
};

export default function WeatherCard({ temperature, condition, humidity, rainfall, windSpeed, location, compact = false }: WeatherCardProps) {
  if (compact) {
    return (
      <div className="card bg-gradient-to-br from-sky-50 to-sky-100 border-sky-200">
        <div className="flex items-center gap-4">
          <span className="text-4xl">{getWeatherEmoji(condition)}</span>
          <div>
            <p className="text-3xl font-extrabold text-charcoal-900">{temperature}°C</p>
            <p className="text-charcoal-600 capitalize">{condition}</p>
          </div>
        </div>
        {location && <p className="text-sm text-charcoal-500 mt-2">{location}</p>}
      </div>
    );
  }

  return (
    <div className="card bg-gradient-to-br from-sky-50 to-sky-100 border-sky-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-5xl">{getWeatherEmoji(condition)}</span>
          <div>
            <p className="text-4xl font-extrabold text-charcoal-900">{temperature}°C</p>
            <p className="text-charcoal-600 capitalize">{condition}</p>
          </div>
        </div>
        {location && (
          <p className="text-sm text-charcoal-500 text-right">{location}</p>
        )}
      </div>
      
      <div className="grid grid-cols-3 gap-4">
        <div className="flex items-center gap-2">
          <Droplets className="h-5 w-5 text-sky-500" />
          <div>
            <p className="text-xs text-charcoal-500">Humidity</p>
            <p className="font-bold text-charcoal-800">{humidity}%</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Cloud className="h-5 w-5 text-sky-500" />
          <div>
            <p className="text-xs text-charcoal-500">Rainfall</p>
            <p className="font-bold text-charcoal-800">{rainfall} mm</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Wind className="h-5 w-5 text-sky-500" />
          <div>
            <p className="text-xs text-charcoal-500">Wind</p>
            <p className="font-bold text-charcoal-800">{windSpeed} m/s</p>
          </div>
        </div>
      </div>
    </div>
  );
}
