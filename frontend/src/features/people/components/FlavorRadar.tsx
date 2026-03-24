import PlotlyChart from '@/components/PlotlyChart';
import { useTheme } from '@mui/material';

interface Props {
  profile: { tag: string; frequency: number }[];
}

export default function FlavorRadar({ profile }: Props) {
  const theme = useTheme();
  if (profile.length === 0) return null;
  const tags = profile.map((p) => p.tag);
  const values = profile.map((p) => p.frequency);
  return (
    <PlotlyChart
      data={[
        {
          type: 'scatterpolar',
          r: [...values, values[0]],
          theta: [...tags, tags[0]],
          fill: 'toself',
          fillcolor: `${theme.palette.primary.main}33`,
          line: { color: theme.palette.primary.main },
          name: 'Flavors',
        },
      ]}
      layout={{
        polar: {
          radialaxis: { visible: true, color: theme.palette.text.secondary },
          angularaxis: { color: theme.palette.text.secondary },
          bgcolor: 'transparent',
        },
        height: 350,
        showlegend: false,
      }}
    />
  );
}
