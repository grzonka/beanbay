import ConfirmDialog from '@/components/ConfirmDialog';
import FlavorTagSelect from '@/components/FlavorTagSelect';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import TasteRadar, { beanTasteToRadar } from '@/components/TasteRadar';
import { fmtDateTime } from '@/utils/date';
import { Archive as ArchiveIcon, Edit as EditIcon } from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Slider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useState } from 'react';
import { useParams } from 'react-router';
import {
  type BeanTaste,
  useDeleteRating,
  useRating,
  useUpsertBeanTaste,
} from './hooks';

interface FlavorTag {
  id: string;
  name: string;
}

interface SliderFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
}

function SliderField({ label, value, onChange }: SliderFieldProps) {
  return (
    <Box>
      <Typography gutterBottom variant="body2">
        {label}: <strong>{value}</strong>
      </Typography>
      <Slider
        value={value}
        onChange={(_, v) => onChange(v as number)}
        min={0}
        max={10}
        step={1}
        marks
        valueLabelDisplay="auto"
        size="small"
      />
    </Box>
  );
}

interface InfoRowProps {
  label: string;
  value: React.ReactNode;
}

function InfoRow({ label, value }: InfoRowProps) {
  return (
    <Stack direction="row" spacing={2} alignItems="flex-start">
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
        {label}
      </Typography>
      <Typography variant="body2">{value ?? '—'}</Typography>
    </Stack>
  );
}

interface EditTasteDialogProps {
  open: boolean;
  onClose: () => void;
  ratingId: string;
  taste: BeanTaste | null;
}

function EditTasteDialog({
  open,
  onClose,
  ratingId,
  taste,
}: EditTasteDialogProps) {
  const { notify } = useNotification();
  const upsert = useUpsertBeanTaste(ratingId);

  const [score, setScore] = useState(taste?.score ?? 5);
  const [acidity, setAcidity] = useState(taste?.acidity ?? 5);
  const [sweetness, setSweetness] = useState(taste?.sweetness ?? 5);
  const [body, setBody] = useState(taste?.body ?? 5);
  const [complexity, setComplexity] = useState(taste?.complexity ?? 5);
  const [aroma, setAroma] = useState(taste?.aroma ?? 5);
  const [cleanCup, setCleanCup] = useState(taste?.clean_cup ?? 5);
  const [notes, setNotes] = useState(taste?.notes ?? '');
  const [flavorTags, setFlavorTags] = useState<FlavorTag[]>(
    taste?.flavor_tags ?? [],
  );

  const handleSubmit = async () => {
    await upsert.mutateAsync({
      score,
      acidity,
      sweetness,
      body,
      complexity,
      aroma,
      clean_cup: cleanCup,
      notes: notes || null,
      flavor_tag_ids: flavorTags.map((t) => t.id),
    });
    notify('Taste updated');
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Taste</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <SliderField label="Score" value={score} onChange={setScore} />
          <SliderField label="Acidity" value={acidity} onChange={setAcidity} />
          <SliderField
            label="Sweetness"
            value={sweetness}
            onChange={setSweetness}
          />
          <SliderField label="Body" value={body} onChange={setBody} />
          <SliderField
            label="Complexity"
            value={complexity}
            onChange={setComplexity}
          />
          <SliderField label="Aroma" value={aroma} onChange={setAroma} />
          <SliderField
            label="Clean Cup"
            value={cleanCup}
            onChange={setCleanCup}
          />
          <TextField
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            rows={3}
          />
          <FlavorTagSelect value={flavorTags} onChange={setFlavorTags} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={upsert.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={upsert.isPending}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function RatingDetailPage() {
  const { ratingId } = useParams<{ ratingId: string }>();
  const { data: rating, isLoading } = useRating(ratingId ?? '');
  const deleteRating = useDeleteRating();
  const { notify } = useNotification();

  const [editTasteOpen, setEditTasteOpen] = useState(false);
  const [retireOpen, setRetireOpen] = useState(false);

  const handleRetire = async () => {
    if (rating) {
      await deleteRating.mutateAsync(rating.id);
      notify('Rating retired');
      setRetireOpen(false);
    }
  };

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="40vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!rating) {
    return <Typography>Rating not found.</Typography>;
  }

  const taste = rating.taste;

  return (
    <>
      <PageHeader
        title={`Rating by ${rating.person_name}`}
        breadcrumbs={[
          { label: 'Beans', to: '/beans' },
          { label: `Rating by ${rating.person_name}` },
        ]}
        actions={
          <Button
            variant="outlined"
            color="warning"
            startIcon={<ArchiveIcon />}
            onClick={() => setRetireOpen(true)}
          >
            Retire
          </Button>
        }
      />

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <InfoRow label="Person" value={rating.person_name} />
            <InfoRow label="Rated At" value={fmtDateTime(rating.rated_at)} />
          </Stack>
        </CardContent>
      </Card>

      {taste ? (
        <>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 2 }}
          >
            <Typography variant="h6">Taste Profile</Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<EditIcon />}
              onClick={() => setEditTasteOpen(true)}
            >
              Edit Taste
            </Button>
          </Stack>

          <Box sx={{ mb: 3 }}>
            <TasteRadar data={beanTasteToRadar(taste)} />
          </Box>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Stack spacing={1.5}>
                {taste.score != null && (
                  <InfoRow label="Score" value={taste.score} />
                )}
                {taste.acidity != null && (
                  <InfoRow label="Acidity" value={taste.acidity} />
                )}
                {taste.sweetness != null && (
                  <InfoRow label="Sweetness" value={taste.sweetness} />
                )}
                {taste.body != null && (
                  <InfoRow label="Body" value={taste.body} />
                )}
                {taste.complexity != null && (
                  <InfoRow label="Complexity" value={taste.complexity} />
                )}
                {taste.aroma != null && (
                  <InfoRow label="Aroma" value={taste.aroma} />
                )}
                {taste.clean_cup != null && (
                  <InfoRow label="Clean Cup" value={taste.clean_cup} />
                )}
                {taste.notes && <InfoRow label="Notes" value={taste.notes} />}
              </Stack>
            </CardContent>
          </Card>

          {taste.flavor_tags.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Flavor Tags
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap">
                {taste.flavor_tags.map((tag) => (
                  <Chip
                    key={tag.id}
                    label={tag.name}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Box>
          )}

          <Divider sx={{ mb: 2 }} />
        </>
      ) : (
        <Box sx={{ mb: 3 }}>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
          >
            <Typography variant="body2" color="text.secondary">
              No taste data recorded.
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<EditIcon />}
              onClick={() => setEditTasteOpen(true)}
            >
              Add Taste
            </Button>
          </Stack>
        </Box>
      )}

      <EditTasteDialog
        open={editTasteOpen}
        onClose={() => setEditTasteOpen(false)}
        ratingId={rating.id}
        taste={taste}
      />

      <ConfirmDialog
        open={retireOpen}
        title="Retire Rating"
        message={`Retire this rating by ${rating.person_name}? It will be hidden but not deleted.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireOpen(false)}
      />
    </>
  );
}
