import { useTheme } from '@mui/material';
import PlotlyChart from './PlotlyChart';

export interface TasteDataPoint {
  axis: string;
  value: number;
}

interface TasteRadarProps {
  data: TasteDataPoint[];
  maxValue?: number;
  size?: number;
}

export default function TasteRadar({
  data,
  maxValue = 10,
  size = 300,
}: TasteRadarProps) {
  const theme = useTheme();
  if (data.length === 0) return null;
  const axes = data.map((d) => d.axis);
  const values = data.map((d) => d.value);

  return (
    <PlotlyChart
      data={[
        {
          type: 'scatterpolar',
          r: [...values, values[0]],
          theta: [...axes, axes[0]],
          fill: 'toself',
          fillcolor: `${theme.palette.primary.main}4D`,
          line: { color: theme.palette.primary.main },
          name: 'Taste',
        },
      ]}
      layout={{
        polar: {
          radialaxis: {
            visible: true,
            range: [0, maxValue],
            color: theme.palette.text.secondary,
          },
          angularaxis: { color: theme.palette.text.secondary },
          bgcolor: 'transparent',
        },
        height: size,
        showlegend: false,
        margin: { t: 30, r: 30, b: 30, l: 30 },
      }}
    />
  );
}

// Helper functions (backwards compatible re-exports)

interface BrewTaste {
  acidity?: number | null;
  sweetness?: number | null;
  body?: number | null;
  bitterness?: number | null;
  balance?: number | null;
  aftertaste?: number | null;
}

export function brewTasteToRadar(taste: BrewTaste): TasteDataPoint[] {
  return [
    { axis: 'Acidity', value: taste.acidity ?? 0 },
    { axis: 'Sweetness', value: taste.sweetness ?? 0 },
    { axis: 'Body', value: taste.body ?? 0 },
    { axis: 'Bitterness', value: taste.bitterness ?? 0 },
    { axis: 'Balance', value: taste.balance ?? 0 },
    { axis: 'Aftertaste', value: taste.aftertaste ?? 0 },
  ];
}

interface BeanTaste {
  acidity?: number | null;
  sweetness?: number | null;
  body?: number | null;
  complexity?: number | null;
  aroma?: number | null;
  clean_cup?: number | null;
}

export function beanTasteToRadar(taste: BeanTaste): TasteDataPoint[] {
  return [
    { axis: 'Acidity', value: taste.acidity ?? 0 },
    { axis: 'Sweetness', value: taste.sweetness ?? 0 },
    { axis: 'Body', value: taste.body ?? 0 },
    { axis: 'Complexity', value: taste.complexity ?? 0 },
    { axis: 'Aroma', value: taste.aroma ?? 0 },
    { axis: 'Clean Cup', value: taste.clean_cup ?? 0 },
  ];
}

interface CuppingScores {
  dry_fragrance?: number | null;
  wet_aroma?: number | null;
  brightness?: number | null;
  flavor?: number | null;
  body?: number | null;
  finish?: number | null;
  sweetness?: number | null;
  clean_cup?: number | null;
  complexity?: number | null;
  uniformity?: number | null;
}

export function cuppingToRadar(scores: CuppingScores): TasteDataPoint[] {
  return [
    { axis: 'Dry Fragrance', value: scores.dry_fragrance ?? 0 },
    { axis: 'Wet Aroma', value: scores.wet_aroma ?? 0 },
    { axis: 'Brightness', value: scores.brightness ?? 0 },
    { axis: 'Flavor', value: scores.flavor ?? 0 },
    { axis: 'Body', value: scores.body ?? 0 },
    { axis: 'Finish', value: scores.finish ?? 0 },
    { axis: 'Sweetness', value: scores.sweetness ?? 0 },
    { axis: 'Clean Cup', value: scores.clean_cup ?? 0 },
    { axis: 'Complexity', value: scores.complexity ?? 0 },
    { axis: 'Uniformity', value: scores.uniformity ?? 0 },
  ];
}
