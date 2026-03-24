import { Box, Typography, useTheme } from '@mui/material';
import PlotlyChart from '@/components/PlotlyChart';
import { useFeatureImportance } from '../hooks';

interface Props { campaignId: string; }

export default function FeatureImportance({ campaignId }: Props) {
  const theme = useTheme();
  const { data, isError } = useFeatureImportance(campaignId);

  if (isError || !data) return <Box sx={{ p: 2, textAlign: 'center' }}><Typography color="text.secondary">Need at least 3 measurements for feature importance</Typography></Box>;

  const names = [...data.parameters].reverse();
  const values = [...data.importance].reverse();

  return <PlotlyChart data={[{ x: values, y: names, type: 'bar', orientation: 'h', marker: { color: theme.palette.primary.main }, hovertemplate: '%{y}: %{x:.4f}<extra></extra>' }]}
    layout={{ xaxis: { title: 'SHAP Importance' }, height: Math.max(200, names.length * 40 + 80), margin: { l: 120 } }} />;
}
