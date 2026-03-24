import PlotlyChart from '@/components/PlotlyChart';
import { Box, Skeleton, Typography, useTheme } from '@mui/material';
import { usePosterior } from '../hooks';

interface Props {
  campaignId: string;
  param: string;
}

export default function ParameterSweepChart({ campaignId, param }: Props) {
  const theme = useTheme();
  const { data, isLoading, isError } = usePosterior(campaignId, param, 50);

  if (isLoading)
    return (
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          {param.replace(/_/g, ' ')}
        </Typography>
        <Skeleton variant="rectangular" height={280} />
      </Box>
    );
  if (isError || !data)
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">
          Need more data for {param}
        </Typography>
      </Box>
    );

  const xValues = data.grid[0];
  const mean = data.mean as number[];
  const std = data.std as number[];
  const upper = mean.map((m, i) => m + std[i]);
  const lower = mean.map((m, i) => m - std[i]);
  const measX = data.measurements
    .map((m) => m.values[param])
    .filter((v) => v != null);
  const measY = data.measurements
    .filter((m) => m.values[param] != null)
    .map((m) => m.score);

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        {param.replace(/_/g, ' ')}
      </Typography>
      <PlotlyChart
        data={[
          {
            x: xValues,
            y: upper,
            mode: 'lines',
            type: 'scatter',
            line: { width: 0 },
            showlegend: false,
            hoverinfo: 'skip' as const,
          },
          {
            x: xValues,
            y: lower,
            mode: 'lines',
            type: 'scatter',
            fill: 'tonexty',
            fillcolor: `${theme.palette.primary.main}22`,
            line: { width: 0 },
            showlegend: false,
            hoverinfo: 'skip' as const,
          },
          {
            x: xValues,
            y: mean,
            mode: 'lines',
            type: 'scatter',
            name: 'Predicted',
            line: { color: theme.palette.primary.main, width: 2 },
            hovertemplate: '%{x:.1f}<br>Score: %{y:.2f}<extra></extra>',
          },
          {
            x: measX,
            y: measY,
            mode: 'markers',
            type: 'scatter',
            name: 'Actual',
            marker: { color: theme.palette.warning.main, size: 8 },
            hovertemplate: '%{x:.1f}<br>Score: %{y:.1f}<extra></extra>',
          },
        ]}
        layout={{
          xaxis: { title: param.replace(/_/g, ' ') },
          yaxis: { title: 'Predicted Score' },
          height: 280,
          showlegend: false,
        }}
      />
    </Box>
  );
}
