export interface WeatherPlace {
  readonly id: string;
  readonly name: string;
  readonly detail: string;
  readonly lat: number;
  readonly lon: number;
}

export interface SearchHit {
  readonly name: string;
  readonly detail: string;
  readonly lat: number;
  readonly lon: number;
}

export interface WeatherUnits {
  readonly temp: 'c' | 'f';
  readonly wind: 'kmh' | 'ms' | 'mph' | 'kn';
  readonly precip: 'mm' | 'in';
  readonly pressure: 'hpa' | 'inhg';
}

export interface PreviewDay {
  readonly label: string;
  readonly tmax: number;
  readonly tmin: number;
  readonly rain: number;
  readonly wind: number;
}

export interface Preview {
  readonly location: string;
  readonly desc: string;
  readonly temp: number;
  readonly feels: number;
  readonly humidity: number;
  readonly wind: number;
  readonly gust: number;
  readonly dirName: string;
  readonly pressure: number;
  readonly uv: number;
  readonly aqi: number | null;
  readonly aqiLevel: string;
  readonly stale: boolean;
  readonly units: WeatherUnits;
  readonly days: readonly PreviewDay[];
}

export interface WeatherOverview {
  readonly places: readonly WeatherPlace[];
  readonly defaultId: string;
  readonly error: '' | 'no_location' | 'unavailable';
  readonly preview: Preview | null;
}
