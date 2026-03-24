import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Typography,
} from '@mui/material';
import { useParams } from 'react-router';
import BrewHistory from '../components/BrewHistory';
import FeatureImportance from '../components/FeatureImportance';
import ParameterHeatmap from '../components/ParameterHeatmap';
import ParameterSweepChart from '../components/ParameterSweepChart';
import PredictionSurface from '../components/PredictionSurface';
import ScoreProgressChart from '../components/ScoreProgressChart';
import UncertaintySurface from '../components/UncertaintySurface';
import { useCampaignDetail, useFeatureImportance } from '../hooks';

const phaseColor: Record<string, 'info' | 'warning' | 'success'> = {
  random: 'info',
  learning: 'warning',
  optimizing: 'success',
};

export default function CampaignDetailPage() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const { data: campaign, isLoading } = useCampaignDetail(campaignId!);
  const { data: shap } = useFeatureImportance(campaignId!);

  if (isLoading) return <LinearProgress />;
  if (!campaign) return null;

  const continuousParams = (campaign.effective_ranges ?? [])
    .filter((r) => r.allowed_values == null)
    .map((r) => r.parameter_name);
  const defaultX = shap?.parameters?.[0] ?? continuousParams[0] ?? '';
  const defaultY = shap?.parameters?.[1] ?? continuousParams[1] ?? '';
  const sweepParams = shap
    ? shap.parameters.slice(0, 4).filter((p) => continuousParams.includes(p))
    : continuousParams;
  const title = `${campaign.bean_name ?? 'Campaign'} — ${campaign.brew_setup_name ?? ''}`;

  return (
    <Box>
      <PageHeader
        title={title}
        breadcrumbs={[
          { label: 'Optimize', to: '/optimize' },
          { label: campaign.bean_name ?? campaignId! },
        ]}
      />

      {/* Stats header */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ minWidth: 140 }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Phase
              </Typography>
              <Chip
                label={campaign.phase}
                color={phaseColor[campaign.phase] ?? 'default'}
                sx={{ mt: 0.5 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard
            label="Shots / Best"
            value={`${campaign.measurement_count} / ${campaign.best_score?.toFixed(1) ?? '—'}`}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard
            label="Convergence"
            value={campaign.convergence?.status.replace(/_/g, ' ') ?? '—'}
          />
        </Grid>
      </Grid>

      <Section title="Score Progress">
        <ScoreProgressChart history={campaign.score_history ?? []} />
      </Section>

      <Section title="Parameter Exploration">
        <ParameterHeatmap
          campaignId={campaignId!}
          params={continuousParams}
          defaultX={defaultX}
          defaultY={defaultY}
        />
      </Section>

      {sweepParams.length > 0 && (
        <Section title="Parameter Sweeps">
          <Grid container spacing={2}>
            {sweepParams.map((param) => (
              <Grid size={{ xs: 12, md: 6 }} key={param}>
                <ParameterSweepChart campaignId={campaignId!} param={param} />
              </Grid>
            ))}
          </Grid>
        </Section>
      )}

      <Section title="Prediction Surface">
        <PredictionSurface
          campaignId={campaignId!}
          params={continuousParams}
          defaultX={defaultX}
          defaultY={defaultY}
        />
      </Section>

      <Section title="Feature Importance">
        <FeatureImportance campaignId={campaignId!} />
      </Section>

      <Section title="Uncertainty Map">
        <UncertaintySurface
          campaignId={campaignId!}
          params={continuousParams}
          defaultX={defaultX}
          defaultY={defaultY}
        />
      </Section>

      <Section title="Brew History">
        <BrewHistory
          beanId={campaign.bean_id}
          brewSetupId={campaign.brew_setup_id}
          effectiveRanges={campaign.effective_ranges ?? []}
        />
      </Section>
    </Box>
  );
}

function Section({
  title,
  children,
}: { title: string; children: React.ReactNode }) {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      {children}
    </Box>
  );
}
