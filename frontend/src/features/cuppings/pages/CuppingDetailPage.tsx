import { useState } from 'react';
import { useParams } from 'react-router';
import {
  Box, Button, Card, CardContent, Chip, CircularProgress,
  Divider, Grid, Stack, Typography,
} from '@mui/material';
import { Edit as EditIcon, Archive as ArchiveIcon } from '@mui/icons-material';
import PageHeader from '@/components/PageHeader';
import ConfirmDialog from '@/components/ConfirmDialog';
import TasteRadar, { cuppingToRadar } from '@/components/TasteRadar';
import { useNotification } from '@/components/NotificationProvider';
import { useCupping, useDeleteCupping } from '../hooks';
import CuppingFormDialog from '../components/CuppingFormDialog';

const SCAA_AXES = [
  { key: 'dry_fragrance', label: 'Dry Fragrance' },
  { key: 'wet_aroma', label: 'Wet Aroma' },
  { key: 'brightness', label: 'Brightness' },
  { key: 'flavor', label: 'Flavor' },
  { key: 'body', label: 'Body' },
  { key: 'finish', label: 'Finish' },
  { key: 'sweetness', label: 'Sweetness' },
  { key: 'clean_cup', label: 'Clean Cup' },
  { key: 'complexity', label: 'Complexity' },
  { key: 'uniformity', label: 'Uniformity' },
] as const;

function ScoreRow({ label, value }: { label: string; value: number | null }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ py: 0.5 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" fontWeight="medium">
        {value != null ? value.toFixed(1) : '—'}
      </Typography>
    </Stack>
  );
}

export default function CuppingDetailPage() {
  const { cuppingId } = useParams<{ cuppingId: string }>();
  const { data: cupping, isLoading } = useCupping(cuppingId ?? '');
  const deleteCupping = useDeleteCupping();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [retireOpen, setRetireOpen] = useState(false);

  const handleRetire = async () => {
    if (cupping) {
      await deleteCupping.mutateAsync(cupping.id);
      notify('Cupping retired');
      setRetireOpen(false);
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="40vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!cupping) {
    return <Typography>Cupping not found.</Typography>;
  }

  const radarData = cuppingToRadar(cupping);
  const cuppingLabel = cupping.cupped_at
    ? `${cupping.person_name} — ${new Date(cupping.cupped_at).toLocaleDateString()}`
    : `Cupping by ${cupping.person_name}`;

  return (
    <>
      <PageHeader
        title={cuppingLabel}
        breadcrumbs={[
          { label: 'Cuppings', to: '/cuppings' },
          { label: cuppingLabel },
        ]}
        actions={
          <>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => setFormOpen(true)}
            >
              Edit
            </Button>
            <Button
              variant="outlined"
              color="warning"
              startIcon={<ArchiveIcon />}
              onClick={() => setRetireOpen(true)}
            >
              Retire
            </Button>
          </>
        }
      />

      {/* Total score hero */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={4} alignItems="center" flexWrap="wrap">
            <Box>
              <Typography variant="caption" color="text.secondary">Total Score</Typography>
              <Typography variant="h2" fontWeight="bold" color="primary">
                {cupping.total_score != null ? cupping.total_score.toFixed(2) : '—'}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Person</Typography>
              <Typography variant="h6">{cupping.person_name}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Cupped At</Typography>
              <Typography variant="body1">
                {cupping.cupped_at ? new Date(cupping.cupped_at).toLocaleString() : '—'}
              </Typography>
            </Box>
            {cupping.cuppers_correction != null && cupping.cuppers_correction !== 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary">Cupper's Correction</Typography>
                <Typography variant="body1">
                  {cupping.cuppers_correction > 0 ? '+' : ''}{cupping.cuppers_correction.toFixed(2)}
                </Typography>
              </Box>
            )}
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* SCAA score breakdown */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>Score Breakdown</Typography>
              <Divider sx={{ mb: 1 }} />
              {SCAA_AXES.map(({ key, label }) => (
                <ScoreRow key={key} label={label} value={cupping[key]} />
              ))}
              {cupping.cuppers_correction != null && (
                <>
                  <Divider sx={{ my: 1 }} />
                  <ScoreRow label="Cupper's Correction" value={cupping.cuppers_correction} />
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Radar chart */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>Taste Profile</Typography>
              <TasteRadar data={radarData} maxValue={9} size={320} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Notes */}
      {cupping.notes && (
        <Card variant="outlined" sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Notes</Typography>
            <Typography variant="body2" whiteSpace="pre-wrap">{cupping.notes}</Typography>
          </CardContent>
        </Card>
      )}

      {/* Flavor tags */}
      {cupping.flavor_tags.length > 0 && (
        <Card variant="outlined" sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Flavor Tags</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {cupping.flavor_tags.map((tag) => (
                <Chip key={tag.id} label={tag.name} size="small" color="primary" variant="outlined" />
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}

      <CuppingFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        cupping={cupping}
      />

      <ConfirmDialog
        open={retireOpen}
        title="Retire Cupping"
        message={`Retire this cupping by ${cupping.person_name}? It will be hidden but not deleted.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireOpen(false)}
      />
    </>
  );
}
