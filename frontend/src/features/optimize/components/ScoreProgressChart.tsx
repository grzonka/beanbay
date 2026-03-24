import PlotlyChart from '@/components/PlotlyChart';
import { useTheme } from '@mui/material';
import type { ScoreHistoryEntry } from '../hooks';

interface Props {
  history: ScoreHistoryEntry[];
}

export default function ScoreProgressChart({ history }: Props) {
  const theme = useTheme();
  const normal = history.filter((e) => !e.is_failed && e.score != null);
  const failed = history.filter((e) => e.is_failed);

  let best = Number.NEGATIVE_INFINITY;
  const cumBest = normal.map((e) => {
    best = Math.max(best, e.score!);
    return { x: e.shot_number, y: best };
  });

  return (
    <PlotlyChart
      data={[
        {
          x: normal.map((e) => e.shot_number),
          y: normal.map((e) => e.score),
          mode: 'markers',
          type: 'scatter',
          name: 'Score',
          marker: { color: theme.palette.warning.main, size: 8 },
          hovertemplate: 'Shot %{x}<br>Score: %{y:.1f}<extra></extra>',
        },
        {
          x: failed.map((e) => e.shot_number),
          y: failed.map(() => 0),
          mode: 'markers',
          type: 'scatter',
          name: 'Failed',
          marker: { color: theme.palette.error.main, symbol: 'x', size: 10 },
          hovertemplate: 'Shot %{x}<br>Failed<extra></extra>',
        },
        {
          x: cumBest.map((p) => p.x),
          y: cumBest.map((p) => p.y),
          mode: 'lines',
          type: 'scatter',
          name: 'Best',
          line: { color: theme.palette.success.main, width: 2 },
          hovertemplate: 'Best: %{y:.1f}<extra></extra>',
        },
      ]}
      layout={{
        xaxis: { title: 'Shot #' },
        yaxis: { title: 'Score', range: [0, 10.5] },
        showlegend: true,
        legend: { orientation: 'h', y: -0.2 },
        height: 350,
      }}
    />
  );
}
