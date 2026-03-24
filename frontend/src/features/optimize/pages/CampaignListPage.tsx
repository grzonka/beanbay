import EmptyState from '@/components/EmptyState';
import PageHeader from '@/components/PageHeader';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Tooltip,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router';
import { useCampaigns } from '../hooks';

const phaseColor: Record<string, 'info' | 'warning' | 'success'> = {
  random: 'info',
  learning: 'warning',
  optimizing: 'success',
};

function scoreColor(score: number | null): string {
  if (score == null) return 'text.secondary';
  if (score >= 8) return 'success.main';
  if (score >= 6) return 'warning.main';
  return 'error.main';
}

export default function CampaignListPage() {
  const navigate = useNavigate();
  const { data: campaigns, isLoading } = useCampaigns();

  return (
    <Box>
      <PageHeader title="Optimization Campaigns" />
      {isLoading && <LinearProgress />}
      {!isLoading && (!campaigns || campaigns.length === 0) && (
        <EmptyState
          title="No campaigns yet"
          description="Campaigns are created automatically when you use the Suggest button in the Brew Wizard."
        />
      )}
      <Grid container spacing={2}>
        {campaigns?.map((c) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={c.id}>
            <Card variant="outlined">
              <CardActionArea onClick={() => navigate(`/optimize/${c.id}`)}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight="bold" noWrap>
                    {c.bean_name ?? 'Unknown bean'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {c.brew_setup_name ?? 'Unknown setup'}
                  </Typography>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      mt: 1.5,
                    }}
                  >
                    <Chip
                      label={c.phase}
                      size="small"
                      color={phaseColor[c.phase] ?? 'default'}
                    />
                    <Typography variant="body2" color="text.secondary">
                      {c.measurement_count} shots
                    </Typography>
                  </Box>
                  {c.best_score != null && (
                    <Typography
                      variant="h5"
                      fontWeight="bold"
                      sx={{ mt: 1, color: scoreColor(c.best_score) }}
                    >
                      {c.best_score.toFixed(1)}
                    </Typography>
                  )}
                  <Tooltip
                    title={`${c.phase} phase — ${c.measurement_count} measurements`}
                  >
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(100, (c.measurement_count / 15) * 100)}
                      sx={{ mt: 1.5, height: 6, borderRadius: 3 }}
                      color={
                        c.phase === 'optimizing'
                          ? 'success'
                          : c.phase === 'learning'
                            ? 'warning'
                            : 'info'
                      }
                    />
                  </Tooltip>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
