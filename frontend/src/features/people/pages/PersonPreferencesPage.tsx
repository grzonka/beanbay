import { useState } from 'react';
import { useParams } from 'react-router';
import { Box, Button, Grid, LinearProgress, Typography } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import PersonFormDialog from '../PersonFormDialog';
import { usePersonPreferences } from '@/features/optimize/hooks';
import TopBeansChart from '../components/TopBeansChart';
import FlavorRadar from '../components/FlavorRadar';
import RoastDonut from '../components/RoastDonut';
import OriginPreferences from '../components/OriginPreferences';
import MethodBreakdown from '../components/MethodBreakdown';
import type { Person } from '../hooks';

export default function PersonPreferencesPage() {
  const { personId } = useParams<{ personId: string }>();
  const { data, isLoading } = usePersonPreferences(personId!);
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) return <LinearProgress />;
  if (!data) return null;

  const { person, brew_stats, top_beans, flavor_profile, roast_preference, origin_preferences, method_breakdown } = data;

  const brewStats = brew_stats as { total_brews: number; avg_score?: number; favorite_method?: string };
  const topBeans = top_beans as { name: string; avg_score: number; brew_count: number }[];
  const flavorProfileArray = Object.entries(flavor_profile as Record<string, number>).map(([tag, frequency]) => ({ tag, frequency }));
  const roastPref = roast_preference as Record<string, number>;
  const origins = origin_preferences as { origin: string; avg_score: number; brew_count: number }[];
  const methods = method_breakdown as { method: string; brew_count: number; avg_score: number }[];

  const editPersonObj = { id: person.id, name: person.name, is_default: false, created_at: '', updated_at: '', retired_at: null, is_retired: false } as Person;

  return (
    <Box>
      <PageHeader
        title={`${person.name}'s Preferences`}
        breadcrumbs={[{ label: 'People', to: '/people' }, { label: person.name }]}
        actions={<Button variant="outlined" startIcon={<EditIcon />} onClick={() => setEditOpen(true)}>Edit</Button>}
      />

      <PersonFormDialog open={editOpen} onClose={() => setEditOpen(false)} person={editPersonObj} />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard label="Total Brews" value={brewStats.total_brews} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard label="Average Score" value={brewStats.avg_score?.toFixed(1) ?? '—'} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatsCard label="Favorite Method" value={brewStats.favorite_method ?? '—'} />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {topBeans.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Top Beans"><TopBeansChart beans={topBeans} /></Section>
          </Grid>
        )}
        {flavorProfileArray.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Flavor Profile"><FlavorRadar profile={flavorProfileArray} /></Section>
          </Grid>
        )}
        {Object.keys(roastPref).length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Roast Preference"><RoastDonut roast={roastPref} /></Section>
          </Grid>
        )}
        {origins.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Section title="Origin Preferences"><OriginPreferences origins={origins} /></Section>
          </Grid>
        )}
        {methods.length > 0 && (
          <Grid size={12}>
            <Section title="Method Breakdown"><MethodBreakdown methods={methods} /></Section>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (<Box><Typography variant="h6" gutterBottom>{title}</Typography>{children}</Box>);
}
