import PlotlyChart from '@/components/PlotlyChart';
import { Box, Skeleton, Typography } from '@mui/material';
import { useState } from 'react';
import { usePosterior } from '../hooks';
import ParamSelector from './ParamSelector';

interface Props {
  campaignId: string;
  params: string[];
  defaultX: string;
  defaultY: string;
}

export default function ParameterHeatmap({
  campaignId,
  params,
  defaultX,
  defaultY,
}: Props) {
  const [xParam, setXParam] = useState(defaultX);
  const [yParam, setYParam] = useState(defaultY);
  const { data, isLoading, isError } = usePosterior(
    campaignId,
    `${xParam},${yParam}`,
    5,
  );

  if (params.length < 2) return null;

  if (isLoading)
    return (
      <>
        <ParamSelector
          params={params}
          xValue={xParam}
          yValue={yParam}
          onXChange={setXParam}
          onYChange={setYParam}
        />
        <Skeleton variant="rectangular" height={400} />
      </>
    );

  const measurements = data?.measurements ?? [];

  if (isError || measurements.length === 0) {
    return (
      <>
        <ParamSelector
          params={params}
          xValue={xParam}
          yValue={yParam}
          onXChange={setXParam}
          onYChange={setYParam}
        />
        <Box sx={{ p: 2, textAlign: 'center' }}>
          <Typography color="text.secondary">
            Need more data for parameter heatmap
          </Typography>
        </Box>
      </>
    );
  }

  const valid = measurements.filter(
    (m) => m.values[xParam] != null && m.values[yParam] != null,
  );

  return (
    <>
      <ParamSelector
        params={params}
        xValue={xParam}
        yValue={yParam}
        onXChange={setXParam}
        onYChange={setYParam}
      />
      <PlotlyChart
        data={[
          {
            x: valid.map((m) => m.values[xParam]),
            y: valid.map((m) => m.values[yParam]),
            mode: 'markers',
            type: 'scatter',
            marker: {
              color: valid.map((m) => m.score),
              colorscale: 'RdYlGn',
              cmin: 1,
              cmax: 10,
              size: 12,
              colorbar: { title: 'Score' },
            },
            hovertemplate: `${xParam}: %{x:.1f}<br>${yParam}: %{y:.1f}<br>Score: %{marker.color:.1f}<extra></extra>`,
          },
        ]}
        layout={{
          xaxis: { title: xParam.replace(/_/g, ' ') },
          yaxis: { title: yParam.replace(/_/g, ' ') },
          height: 400,
        }}
      />
    </>
  );
}
