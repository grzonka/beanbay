import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import FlavorTagSelect from '@/components/FlavorTagSelect';
import { useNotification } from '@/components/NotificationProvider';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { type Cupping, useCreateCupping, useUpdateCupping } from '../hooks';

interface OptionItem {
  id: string;
  name: string;
}

interface FlavorTag {
  id: string;
  name: string;
}

interface CuppingFormDialogProps {
  open: boolean;
  onClose: () => void;
  cupping?: Cupping | null;
}

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

type ScaaKey = (typeof SCAA_AXES)[number]['key'];

type ScaaScores = Record<ScaaKey, number>;

const DEFAULT_SCORES: ScaaScores = {
  dry_fragrance: 7,
  wet_aroma: 7,
  brightness: 7,
  flavor: 7,
  body: 7,
  finish: 7,
  sweetness: 7,
  clean_cup: 7,
  complexity: 7,
  uniformity: 7,
};

function calcAutoTotal(scores: ScaaScores, correction: number): number {
  const sum = Object.values(scores).reduce((acc, v) => acc + v, 0);
  return Math.round((sum + correction) * 100) / 100;
}

function CreatePersonForm({
  initialName,
  onCreated,
  onCancel,
}: {
  initialName: string;
  onCreated: (item: OptionItem) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initialName);
  const { notify } = useNotification();

  const handleSubmit = async () => {
    const { data } = await apiClient.post<OptionItem>('/people', { name });
    notify('Person created');
    onCreated(data);
  };

  return (
    <Stack spacing={2} sx={{ pt: 1 }}>
      <TextField
        label="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        autoFocus
      />
      <Stack direction="row" spacing={1} justifyContent="flex-end">
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!name.trim()}
        >
          Create
        </Button>
      </Stack>
    </Stack>
  );
}

export default function CuppingFormDialog({
  open,
  onClose,
  cupping,
}: CuppingFormDialogProps) {
  const isEdit = !!cupping;
  const create = useCreateCupping();
  const update = useUpdateCupping();
  const { notify } = useNotification();

  // Form state
  const [bag, setBag] = useState<OptionItem | null>(null);
  const [person, setPerson] = useState<OptionItem | null>(null);
  const [cuppedAt, setCuppedAt] = useState('');
  const [scores, setScores] = useState<ScaaScores>(DEFAULT_SCORES);
  const [cuppersCorrection, setCuppersCorrection] = useState(0);
  const [manualTotal, setManualTotal] = useState(false);
  const [totalScore, setTotalScore] = useState<number>(0);
  const [notes, setNotes] = useState('');
  const [flavorTags, setFlavorTags] = useState<FlavorTag[]>([]);

  const autoTotal = calcAutoTotal(scores, cuppersCorrection);

  const { data: bagData } = useQuery({
    queryKey: ['bags', cupping?.bag_id, 'resolve'],
    queryFn: async () => {
      const [bagRes, beansRes] = await Promise.all([
        apiClient.get(`/bags/${cupping?.bag_id}`),
        apiClient.get('/beans', { params: { limit: 200 } }),
      ]);
      const beanMap = new Map();
      beansRes.data.items.forEach((b: any) => beanMap.set(b.id, b.name));
      const bagResult = bagRes.data;
      return {
        id: bagResult.id,
        name: `${beanMap.get(bagResult.bean_id) ?? 'Unknown'} — ${bagResult.weight}g`,
      };
    },
    enabled: !!cupping?.bag_id && open,
  });

  useEffect(() => {
    if (bagData && cupping) {
      setBag(bagData);
    }
  }, [bagData, cupping]);

  useEffect(() => {
    if (!manualTotal) {
      setTotalScore(autoTotal);
    }
  }, [autoTotal, manualTotal]);

  useEffect(() => {
    if (cupping) {
      if (bagData) {
        setBag(bagData);
      } else {
        setBag({ id: cupping.bag_id, name: cupping.bag_id });
      }
      setPerson({ id: cupping.person_id, name: cupping.person_name });
      setCuppedAt(cupping.cupped_at ? cupping.cupped_at.slice(0, 16) : '');
      setScores({
        dry_fragrance: cupping.dry_fragrance ?? 7,
        wet_aroma: cupping.wet_aroma ?? 7,
        brightness: cupping.brightness ?? 7,
        flavor: cupping.flavor ?? 7,
        body: cupping.body ?? 7,
        finish: cupping.finish ?? 7,
        sweetness: cupping.sweetness ?? 7,
        clean_cup: cupping.clean_cup ?? 7,
        complexity: cupping.complexity ?? 7,
        uniformity: cupping.uniformity ?? 7,
      });
      setCuppersCorrection(cupping.cuppers_correction ?? 0);
      setManualTotal(false);
      setTotalScore(cupping.total_score ?? 0);
      setNotes(cupping.notes ?? '');
      setFlavorTags(
        cupping.flavor_tags.map((t) => ({ id: t.id, name: t.name })),
      );
    } else {
      setBag(null);
      setPerson(null);
      setCuppedAt(new Date().toISOString().slice(0, 16));
      setScores(DEFAULT_SCORES);
      setCuppersCorrection(0);
      setManualTotal(false);
      setTotalScore(calcAutoTotal(DEFAULT_SCORES, 0));
      setNotes('');
      setFlavorTags([]);
    }
  }, [cupping, open]);

  const handleScoreChange = (key: ScaaKey, value: number) => {
    setScores((prev) => ({ ...prev, [key]: value }));
  };

  const buildBody = () => ({
    bag_id: bag?.id ?? null,
    person_id: person?.id ?? null,
    cupped_at: cuppedAt || null,
    ...scores,
    cuppers_correction: cuppersCorrection,
    total_score: totalScore,
    notes: notes || null,
    flavor_tag_ids: flavorTags.map((t) => t.id),
  });

  const handleSubmit = async () => {
    if (isEdit) {
      await update.mutateAsync({ id: cupping?.id, ...buildBody() });
      notify('Cupping updated');
    } else {
      await create.mutateAsync(buildBody());
      notify('Cupping created');
    }
    onClose();
  };

  const isPending = create.isPending || update.isPending;
  const isValid = !!bag && !!person;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Cupping' : 'Add Cupping'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <AutocompleteCreate<OptionItem>
            label="Bag"
            queryKey={['bags']}
            fetchFn={async (q) => {
              const [{ data }, { data: beansData }] = await Promise.all([
                apiClient.get('/bags', { params: { q, limit: 50 } }),
                apiClient.get('/beans', { params: { limit: 200 } }),
              ]);
              const beanMap = new Map<string, string>();
              for (const bean of beansData.items) {
                beanMap.set(bean.id, bean.name);
              }
              return {
                ...data,
                items: data.items.map((bag: any) => {
                  const beanName =
                    beanMap.get(bag.bean_id) ?? `Bag ${bag.id.slice(0, 8)}`;
                  const weightStr = bag.weight != null ? `${bag.weight}g` : '';
                  const dateStr = bag.roast_date ? ` (${bag.roast_date})` : '';
                  return {
                    ...bag,
                    name:
                      [beanName, weightStr].filter(Boolean).join(' — ') +
                      dateStr,
                  };
                }),
              };
            }}
            value={bag}
            onChange={(v) => setBag(v as OptionItem | null)}
            required
          />

          <AutocompleteCreate<OptionItem>
            label="Person"
            queryKey={['people']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/people', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={person}
            onChange={(v) => setPerson(v as OptionItem | null)}
            required
            renderCreateForm={(props) => <CreatePersonForm {...props} />}
          />

          <TextField
            label="Cupped At"
            type="datetime-local"
            value={cuppedAt}
            onChange={(e) => setCuppedAt(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1 }}>
            SCAA Score Axes (0–9, step 0.5)
          </Typography>

          {SCAA_AXES.map(({ key, label }) => (
            <Box key={key}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography variant="body2">{label}</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {scores[key].toFixed(1)}
                </Typography>
              </Stack>
              <Slider
                value={scores[key]}
                onChange={(_, v) => handleScoreChange(key, v as number)}
                min={0}
                max={9}
                step={0.5}
                valueLabelDisplay="auto"
                size="small"
              />
            </Box>
          ))}

          <TextField
            label="Cupper's Correction"
            type="number"
            value={cuppersCorrection}
            onChange={(e) => setCuppersCorrection(Number(e.target.value))}
            slotProps={{ input: { inputProps: { step: 0.5 } } }}
          />

          <Box>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
            >
              <Typography variant="body2" fontWeight="bold">
                Total Score:{' '}
                {manualTotal ? totalScore.toFixed(2) : autoTotal.toFixed(2)}
              </Typography>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={manualTotal}
                    onChange={(_, c) => {
                      setManualTotal(c);
                      if (!c) setTotalScore(autoTotal);
                    }}
                  />
                }
                label="Override"
              />
            </Stack>
            {manualTotal && (
              <TextField
                label="Manual Total Score"
                type="number"
                value={totalScore}
                onChange={(e) => setTotalScore(Number(e.target.value))}
                fullWidth
                size="small"
                sx={{ mt: 1 }}
                slotProps={{ input: { inputProps: { step: 0.25 } } }}
              />
            )}
          </Box>

          <FlavorTagSelect value={flavorTags} onChange={setFlavorTags} />

          <TextField
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            rows={3}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!isValid || isPending}
        >
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
