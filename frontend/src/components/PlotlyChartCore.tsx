import { useTheme } from '@mui/material';
import Plotly from 'plotly.js-dist-min';
import _createPlotlyComponent from 'react-plotly.js/factory';

// CJS/ESM interop: factory may be wrapped in { default: fn } due to __esModule flag
const createPlotlyComponent =
  typeof _createPlotlyComponent === 'function'
    ? _createPlotlyComponent
    : (_createPlotlyComponent as any).default;

const Plot = createPlotlyComponent(Plotly);

interface PlotlyChartProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  style?: React.CSSProperties;
  config?: Partial<Plotly.Config>;
}

export default function PlotlyChartCore({
  data,
  layout = {},
  style,
  config,
}: PlotlyChartProps) {
  const theme = useTheme();

  const themedLayout: Partial<Plotly.Layout> = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      color: theme.palette.text.primary,
      family: theme.typography.fontFamily as string,
    },
    xaxis: {
      gridcolor: theme.palette.divider,
      zerolinecolor: theme.palette.divider,
      ...layout.xaxis,
    },
    yaxis: {
      gridcolor: theme.palette.divider,
      zerolinecolor: theme.palette.divider,
      ...layout.yaxis,
    },
    margin: { t: 40, r: 20, b: 50, l: 55 },
    ...layout,
  };

  const defaultConfig: Partial<Plotly.Config> = {
    displayModeBar: false,
    responsive: true,
    ...config,
  };

  return (
    <Plot
      data={data}
      layout={themedLayout}
      config={defaultConfig}
      style={{ width: '100%', height: '100%', ...style }}
      useResizeHandler
    />
  );
}
