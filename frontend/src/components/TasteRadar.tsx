// frontend/src/components/TasteRadar.tsx
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
} from 'recharts';
import { useTheme } from '@mui/material';

interface TasteDataPoint { axis: string; value: number | null; }

interface TasteRadarProps { data: TasteDataPoint[]; maxValue?: number; size?: number; }

export default function TasteRadar({ data, maxValue = 10, size = 300 }: TasteRadarProps) {
  const theme = useTheme();
  const chartData = data.map((d) => ({ axis: d.axis, value: d.value ?? 0 }));

  return (
    <ResponsiveContainer width="100%" height={size}>
      <RadarChart data={chartData}>
        <PolarGrid stroke={theme.palette.divider} />
        <PolarAngleAxis dataKey="axis" tick={{ fill: theme.palette.text.secondary, fontSize: 12 }} />
        <PolarRadiusAxis domain={[0, maxValue]} tick={{ fill: theme.palette.text.secondary, fontSize: 10 }} axisLine={false} />
        <Radar name="Taste" dataKey="value" stroke={theme.palette.primary.main} fill={theme.palette.primary.main} fillOpacity={0.3} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

export function brewTasteToRadar(taste: {
  acidity?: number | null; sweetness?: number | null; body?: number | null;
  bitterness?: number | null; balance?: number | null; aftertaste?: number | null;
}): TasteDataPoint[] {
  return [
    { axis: 'Acidity', value: taste.acidity ?? null },
    { axis: 'Sweetness', value: taste.sweetness ?? null },
    { axis: 'Body', value: taste.body ?? null },
    { axis: 'Bitterness', value: taste.bitterness ?? null },
    { axis: 'Balance', value: taste.balance ?? null },
    { axis: 'Aftertaste', value: taste.aftertaste ?? null },
  ];
}

export function beanTasteToRadar(taste: {
  acidity?: number | null; sweetness?: number | null; body?: number | null;
  complexity?: number | null; aroma?: number | null; clean_cup?: number | null;
}): TasteDataPoint[] {
  return [
    { axis: 'Acidity', value: taste.acidity ?? null },
    { axis: 'Sweetness', value: taste.sweetness ?? null },
    { axis: 'Body', value: taste.body ?? null },
    { axis: 'Complexity', value: taste.complexity ?? null },
    { axis: 'Aroma', value: taste.aroma ?? null },
    { axis: 'Clean Cup', value: taste.clean_cup ?? null },
  ];
}

export function cuppingToRadar(cupping: {
  dry_fragrance?: number | null; wet_aroma?: number | null; brightness?: number | null;
  flavor?: number | null; body?: number | null; finish?: number | null;
  sweetness?: number | null; clean_cup?: number | null; complexity?: number | null;
  uniformity?: number | null;
}): TasteDataPoint[] {
  return [
    { axis: 'Dry Fragrance', value: cupping.dry_fragrance ?? null },
    { axis: 'Wet Aroma', value: cupping.wet_aroma ?? null },
    { axis: 'Brightness', value: cupping.brightness ?? null },
    { axis: 'Flavor', value: cupping.flavor ?? null },
    { axis: 'Body', value: cupping.body ?? null },
    { axis: 'Finish', value: cupping.finish ?? null },
    { axis: 'Sweetness', value: cupping.sweetness ?? null },
    { axis: 'Clean Cup', value: cupping.clean_cup ?? null },
    { axis: 'Complexity', value: cupping.complexity ?? null },
    { axis: 'Uniformity', value: cupping.uniformity ?? null },
  ];
}
