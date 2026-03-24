import PlotlyChart from '@/components/PlotlyChart';
import { useTheme } from '@mui/material';

interface Props {
  beans: { name: string; avg_score: number; brew_count: number }[];
}

export default function TopBeansChart({ beans }: Props) {
  const theme = useTheme();
  const sorted = [...beans].sort((a, b) => b.avg_score - a.avg_score);
  return (
    <PlotlyChart
      data={[
        {
          x: sorted.map((b) => b.avg_score),
          y: sorted.map((b) => b.name),
          type: 'bar',
          orientation: 'h',
          marker: { color: theme.palette.primary.main },
          text: sorted.map((b) => `${b.brew_count} brews`),
          textposition: 'auto',
          hovertemplate: '%{y}<br>Avg: %{x:.1f}<br>%{text}<extra></extra>',
        },
      ]}
      layout={{
        xaxis: { title: 'Avg Score', range: [0, 10] },
        height: Math.max(200, sorted.length * 35 + 80),
        margin: { l: 140 },
      }}
    />
  );
}
