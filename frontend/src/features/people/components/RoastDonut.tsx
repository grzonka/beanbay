import PlotlyChart from '@/components/PlotlyChart';

interface Props {
  roast: Record<string, number>;
}

export default function RoastDonut({ roast }: Props) {
  const labels = Object.keys(roast);
  const values = Object.values(roast);
  if (labels.length === 0) return null;
  return (
    <PlotlyChart
      data={[
        {
          labels,
          values,
          type: 'pie',
          hole: 0.5,
          marker: { colors: ['#f9e79f', '#d4a574', '#6d4c41'] },
          textinfo: 'label+percent',
          hovertemplate: '%{label}: %{value} brews (%{percent})<extra></extra>',
        },
      ]}
      layout={{
        height: 300,
        showlegend: true,
        legend: { orientation: 'h', y: -0.1 },
      }}
    />
  );
}
