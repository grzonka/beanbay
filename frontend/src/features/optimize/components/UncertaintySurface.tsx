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

export default function UncertaintySurface({
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
            Need more data for uncertainty map
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
            z: data.std as number[][],
            type: 'contour',
            colorscale: [
              [0, '#1a237e'],
              [0.5, '#42a5f5'],
              [1, '#ffee58'],
            ],
            colorbar: { title: 'Uncertainty' },
            hovertemplate: `${xParam}: %{x:.1f}<br>${yParam}: %{y:.1f}<br>Std: %{z:.3f}<extra></extra>`,
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
