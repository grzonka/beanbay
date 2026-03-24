import PlotlyChart from '@/components/PlotlyChart';
import { useTheme } from '@mui/material';

interface Props {
  origins: { origin: string; avg_score: number; brew_count: number }[];
}

export default function OriginPreferences({ origins }: Props) {
  const theme = useTheme();
  const sorted = [...origins].sort((a, b) => b.avg_score - a.avg_score);
  return (
    <PlotlyChart
      data={[
        {
          x: sorted.map((o) => o.avg_score),
          y: sorted.map((o) => o.origin),
          type: 'bar',
          orientation: 'h',
          marker: { color: theme.palette.secondary.main },
          hovertemplate: '%{y}<br>Avg: %{x:.1f}<extra></extra>',
        },
      ]}
      layout={{
        xaxis: { title: 'Avg Score', range: [0, 10] },
        height: Math.max(200, sorted.length * 35 + 80),
        margin: { l: 120 },
      }}
    />
  );
}
