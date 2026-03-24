import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import TasteRadar, { type TasteDataPoint } from '@/components/TasteRadar';
import { usePersonPreferences } from '@/features/optimize/hooks';
import EditIcon from '@mui/icons-material/Edit';
import { Box, Button, Grid, LinearProgress, Typography } from '@mui/material';
import { useState } from 'react';
import { useParams } from 'react-router';
import PersonFormDialog from '../PersonFormDialog';
import FlavorRadar from '../components/FlavorRadar';
import MethodBreakdown from '../components/MethodBreakdown';
import OriginPreferences from '../components/OriginPreferences';
import RoastDonut from '../components/RoastDonut';
import TopBeansChart from '../components/TopBeansChart';
import type { Person } from '../hooks';

export default function PersonPreferencesPage() {
  const { personId } = useParams<{ personId: string }>();
  const { data, isLoading } = usePersonPreferences(personId!);
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) return <LinearProgress />;
  if (!data) return null;

  const {
    person,
    brew_stats,
    top_beans,
    flavor_profile,
    roast_preference,
    origin_preferences,
    method_breakdown,
    taste_profile,
    taste_profile_brew_count,
  } = data;

  const brewStats = brew_stats as {
    total_brews: number;
    avg_score?: number;
    favorite_method?: string;
  };
  const topBeans = top_beans as {
    name: string;
    avg_score: number;
    brew_count: number;
  }[];
  const flavorProfileArray = Object.entries(
    flavor_profile as Record<string, number>,
  ).map(([tag, frequency]) => ({ tag, frequency }));
  const roastPref = roast_preference as Record<string, number>;
  const origins = origin_preferences as {
    origin: string;
    avg_score: number;
    brew_count: number;
  }[];
  const methods = method_breakdown as {
    method: string;
    brew_count: number;
    avg_score: number;
  }[];

  const editPersonObj = {
    id: person.id,
    name: person.name,
    is_default: false,
    created_at: '',
    updated_at: '',
    retired_at: null,
    is_retired: false,
  } as Person;

  return (
    <Box>
      <PageHeader
        title={`${person.name}'s Preferences`}
        breadcrumbs={[
          { label: 'People', to: '/people' },
          { label: person.name },
        ]}
        actions={
          <Button
            variant="outlined"
            startIcon={<EditIcon />}
            onClick={() => setEditOpen(true)}
          >
            Edit
          </Button>
        }
      />

      <PersonFormDialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        person={editPersonObj}
      />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard label="Total Brews" value={brewStats.total_brews} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard
            label="Average Score"
            value={brewStats.avg_score?.toFixed(1) ?? '—'}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard
            label="Favorite Method"
            value={brewStats.favorite_method ?? '—'}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {topBeans.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Top Beans">
              <TopBeansChart beans={topBeans} />
            </Section>
          </Grid>
        )}
        {taste_profile && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Taste Profile">
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Based on your {taste_profile_brew_count} best brews
              </Typography>
              <TasteRadar data={profileToRadar(taste_profile)} size={300} />
            </Section>
          </Grid>
        )}
        {flavorProfileArray.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Flavor Profile">
              <FlavorRadar profile={flavorProfileArray} />
            </Section>
          </Grid>
        )}
        {Object.keys(roastPref).length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Roast Preference">
              <RoastDonut roast={roastPref} />
            </Section>
          </Grid>
        )}
        {origins.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Origin Preferences">
              <OriginPreferences origins={origins} />
            </Section>
          </Grid>
        )}
        {methods.length > 0 && (
          <Grid size={12}>
            <Section title="Method Breakdown">
              <MethodBreakdown methods={methods} />
            </Section>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

function profileToRadar(profile: {
  acidity: number | null;
  sweetness: number | null;
  body: number | null;
  bitterness: number | null;
  balance: number | null;
  aftertaste: number | null;
}): TasteDataPoint[] {
  return [
    { axis: 'Acidity', value: profile.acidity ?? 0 },
    { axis: 'Sweetness', value: profile.sweetness ?? 0 },
    { axis: 'Body', value: profile.body ?? 0 },
    { axis: 'Bitterness', value: profile.bitterness ?? 0 },
    { axis: 'Balance', value: profile.balance ?? 0 },
    { axis: 'Aftertaste', value: profile.aftertaste ?? 0 },
  ];
}

function Section({
  title,
  children,
}: { title: string; children: React.ReactNode }) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      {children}
    </Box>
  );
}
