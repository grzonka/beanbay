import { Suspense, lazy } from 'react';
import type { ComponentProps } from 'react';

const PlotlyChartCore = lazy(() => import('./PlotlyChartCore'));

type PlotlyChartProps = ComponentProps<typeof PlotlyChartCore>;

export default function PlotlyChart(props: PlotlyChartProps) {
  return (
    <Suspense fallback={<div style={{ width: '100%', height: '100%' }} />}>
      <PlotlyChartCore {...props} />
    </Suspense>
  );
}
