import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import { useCampaigns } from '@/features/optimize/hooks';
import {
  Coffee as CoffeeIcon,
  LocalCafe as LocalCafeIcon,
  AutoFixHigh as OptimizeIcon,
} from '@mui/icons-material';
import {
  Box,
  Divider,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router';
import {
  useBeanStats,
  useBrewStats,
  useCuppingStats,
  useEquipmentStats,
  useRecentBrews,
  useTasteStats,
} from './hooks';

function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function StatRow({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
      {children}
    </Box>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="overline"
      color="text.secondary"
      sx={{ mb: 1, display: 'block' }}
    >
      {children}
    </Typography>
  );
}

export default function DashboardPage() {
  const { data: brewStats, isLoading: brewLoading } = useBrewStats();
  const { data: beanStats, isLoading: beanLoading } = useBeanStats();
  const { data: tasteStats, isLoading: tasteLoading } = useTasteStats();
  const { data: equipmentStats, isLoading: equipmentLoading } =
    useEquipmentStats();
  const { data: cuppingStats, isLoading: cuppingLoading } = useCuppingStats();
  const { data: recentBrews, isLoading: recentLoading } = useRecentBrews();
  const { data: campaigns } = useCampaigns();
  const navigate = useNavigate();
  const activeCampaigns = campaigns?.length ?? 0;
  const bestOverall = campaigns?.reduce(
    (best, c) =>
      c.best_score != null && (best == null || c.best_score > best)
        ? c.best_score
        : best,
    null as number | null,
  );

  const failRateDisplay =
    brewStats?.fail_rate != null
      ? `${(brewStats.fail_rate * 100).toFixed(1)}%`
      : null;

  const avgDoseDisplay =
    brewStats?.avg_dose_g != null
      ? `${brewStats.avg_dose_g.toFixed(1)}g`
      : null;

  return (
    <>
      <PageHeader title="Dashboard" />

      {/* Row 1 — Brews */}
      <SectionLabel>Brews</SectionLabel>
      <StatRow>
        <StatsCard
          label="Total Brews"
          value={brewStats?.total}
          icon={<CoffeeIcon fontSize="inherit" />}
          loading={brewLoading}
        />
        <StatsCard
          label="This Week"
          value={brewStats?.this_week}
          loading={brewLoading}
        />
        <StatsCard
          label="Fail Rate"
          value={failRateDisplay}
          loading={brewLoading}
        />
        <StatsCard
          label="Avg Dose"
          value={avgDoseDisplay}
          loading={brewLoading}
        />
      </StatRow>

      {/* Row 2 — Beans */}
      <SectionLabel>Beans</SectionLabel>
      <StatRow>
        <StatsCard
          label="Total Beans"
          value={beanStats?.total_beans}
          icon={<LocalCafeIcon fontSize="inherit" />}
          loading={beanLoading}
        />
        <StatsCard
          label="Active Bags"
          value={beanStats?.bags_active}
          loading={beanLoading}
        />
        <StatsCard
          label="Bags Unopened"
          value={beanStats?.bags_unopened}
          loading={beanLoading}
        />
      </StatRow>

      {/* Row 3 — Taste */}
      <SectionLabel>Taste</SectionLabel>
      <StatRow>
        <StatsCard
          label="Best Brew Score"
          value={tasteStats?.brew_taste?.best_score?.toFixed(1) ?? null}
          loading={tasteLoading}
        />
        <StatsCard
          label="Best Bean Score"
          value={tasteStats?.bean_taste?.best_score?.toFixed(1) ?? null}
          loading={tasteLoading}
        />
      </StatRow>

      {/* Row 4 — Equipment */}
      <SectionLabel>Equipment</SectionLabel>
      <StatRow>
        <StatsCard
          label="Total Grinders"
          value={equipmentStats?.total_grinders}
          loading={equipmentLoading}
        />
        <StatsCard
          label="Total Brewers"
          value={equipmentStats?.total_brewers}
          loading={equipmentLoading}
        />
        <StatsCard
          label="Most Used Method"
          value={equipmentStats?.most_used_method?.name ?? null}
          loading={equipmentLoading}
        />
      </StatRow>

      {/* Row 5 — Cuppings */}
      <SectionLabel>Cuppings</SectionLabel>
      <StatRow>
        <StatsCard
          label="Total Cuppings"
          value={cuppingStats?.total}
          loading={cuppingLoading}
        />
        <StatsCard
          label="Avg Score"
          value={cuppingStats?.avg_total_score?.toFixed(1) ?? null}
          loading={cuppingLoading}
        />
        <StatsCard
          label="Best Score"
          value={cuppingStats?.best_total_score?.toFixed(1) ?? null}
          loading={cuppingLoading}
        />
      </StatRow>

      {/* Optimization */}
      <SectionLabel>Optimization</SectionLabel>
      <StatRow>
        <Box onClick={() => navigate('/optimize')} sx={{ cursor: 'pointer' }}>
          <StatsCard
            label="Active Campaigns"
            value={activeCampaigns}
            icon={<OptimizeIcon />}
          />
        </Box>
        <StatsCard label="Best Score" value={bestOverall?.toFixed(1) ?? '—'} />
      </StatRow>

      {/* Recent Brews */}
      <Divider sx={{ my: 3 }} />
      <Typography variant="h6" gutterBottom>
        Recent Brews
      </Typography>
      {recentLoading ? (
        <Typography variant="body2" color="text.secondary">
          Loading...
        </Typography>
      ) : recentBrews?.items?.length ? (
        <List disablePadding>
          {recentBrews.items.map((brew) => (
            <ListItem key={brew.id} disableGutters divider>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body1" component="span">
                      {brew.bean_name}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      component="span"
                    >
                      · {brew.brew_method_name}
                    </Typography>
                    {brew.score != null && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        component="span"
                      >
                        · {brew.score.toFixed(1)}
                      </Typography>
                    )}
                  </Box>
                }
                secondary={formatRelativeTime(brew.brewed_at)}
              />
            </ListItem>
          ))}
        </List>
      ) : (
        <Typography variant="body2" color="text.secondary">
          No brews yet.
        </Typography>
      )}
    </>
  );
}
