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

export default function PredictionSurface({
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
    20,
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
        <Skeleton variant="rectangular" height={450} />
      </>
    );
  if (isError || !data)
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
            Need more data for prediction surface
          </Typography>
        </Box>
      </>
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
            x: data.grid[0],
            y: data.grid[1],
            z: data.mean as number[][],
            type: 'contour',
            colorscale: 'RdYlGn',
            colorbar: { title: 'Score' },
            hovertemplate: `${xParam}: %{x:.1f}<br>${yParam}: %{y:.1f}<br>Score: %{z:.2f}<extra></extra>`,
          },
          {
            x: data.measurements.map((m) => m.values[xParam]),
            y: data.measurements.map((m) => m.values[yParam]),
            mode: 'markers',
            type: 'scatter',
            name: 'Measurements',
            marker: {
              color: 'white',
              size: 7,
              line: { color: 'black', width: 1 },
            },
            hovertemplate: `${xParam}: %{x:.1f}<br>${yParam}: %{y:.1f}<extra></extra>`,
          },
        ]}
        layout={{
          xaxis: { title: xParam.replace(/_/g, ' ') },
          yaxis: { title: yParam.replace(/_/g, ' ') },
          height: 450,
        }}
      />
    </>
  );
}
