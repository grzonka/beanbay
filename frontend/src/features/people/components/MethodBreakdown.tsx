import PlotlyChart from '@/components/PlotlyChart';
import { useTheme } from '@mui/material';

interface Props {
  methods: { method: string; brew_count: number; avg_score: number }[];
}

export default function MethodBreakdown({ methods }: Props) {
  const theme = useTheme();
  return (
    <PlotlyChart
      data={[
        {
          x: methods.map((m) => m.method),
          y: methods.map((m) => m.brew_count),
          type: 'bar',
          name: 'Brews',
          marker: { color: theme.palette.primary.main },
          hovertemplate: '%{x}<br>Brews: %{y}<extra></extra>',
        },
        {
          x: methods.map((m) => m.method),
          y: methods.map((m) => m.avg_score),
          type: 'bar',
          name: 'Avg Score',
          marker: { color: theme.palette.secondary.main },
          yaxis: 'y2',
          hovertemplate: '%{x}<br>Avg: %{y:.1f}<extra></extra>',
        },
      ]}
      layout={{
        barmode: 'group',
        yaxis: { title: 'Brew Count' },
        yaxis2: {
          title: 'Avg Score',
          overlaying: 'y',
          side: 'right',
          range: [0, 10],
        },
        height: 350,
        legend: { orientation: 'h', y: -0.2 },
      }}
    />
  );
}
