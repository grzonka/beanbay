import { useState } from 'react';
import { useParams } from 'react-router';
import {
  Box, Button, Card, CardContent, Chip, CircularProgress,
  Dialog, DialogActions, DialogContent, DialogTitle,
  Divider, Grid, Slider, Stack, TextField, Typography,
} from '@mui/material';
import {
  Edit as EditIcon,
  Archive as ArchiveIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import PageHeader from '@/components/PageHeader';
import ConfirmDialog from '@/components/ConfirmDialog';
import TasteRadar, { brewTasteToRadar } from '@/components/TasteRadar';
import FlavorTagSelect from '@/components/FlavorTagSelect';
import { useNotification } from '@/components/NotificationProvider';
import {
  useBrew, useUpdateBrew, useDeleteBrew,
  useUpsertBrewTaste, useDeleteBrewTaste,
  type Brew, type BrewTaste,
} from '../hooks';

// ─── helpers ────────────────────────────────────────────────────────────────

function fmt(v: number | null | undefined, unit?: string): string {
  if (v == null) return '—';
  return unit ? `${v} ${unit}` : String(v);
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—';
  return new Date(s).toLocaleString();
}

// ─── InfoRow ────────────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={2} alignItems="flex-start">
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 160 }}>
        {label}
      </Typography>
      <Typography variant="body2" component="span">
        {value ?? '—'}
      </Typography>
    </Stack>
  );
}

// ─── BrewInfoCard ────────────────────────────────────────────────────────────

function BrewInfoCard({ brew }: { brew: Brew }) {
  const setup = brew.brew_setup;
  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Grid container spacing={3}>
          {/* Left: identity */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Identity
            </Typography>
            <Stack spacing={1}>
              <InfoRow label="Bean" value={brew.bag?.bean_name} />
              <InfoRow label="Person" value={brew.person?.name} />
              <InfoRow label="Brewed At" value={fmtDate(brew.brewed_at)} />
              {brew.is_failed && (
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 160 }}>
                    Status
                  </Typography>
                  <Chip label="Failed" size="small" color="error" />
                </Stack>
              )}
            </Stack>
          </Grid>

          {/* Right: setup */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Setup
            </Typography>
            <Stack spacing={1}>
              <InfoRow label="Method" value={setup?.brew_method_name} />
              <InfoRow label="Grinder" value={setup?.grinder_name} />
              <InfoRow label="Brewer" value={setup?.brewer_name} />
              <InfoRow label="Paper" value={setup?.paper_name} />
              <InfoRow label="Water" value={setup?.water_name} />
            </Stack>
          </Grid>

          {/* Parameters */}
          <Grid size={{ xs: 12 }}>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Parameters
            </Typography>
            <Grid container spacing={1}>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Dose" value={fmt(brew.dose, 'g')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Yield" value={fmt(brew.yield_amount, 'g')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Grind Setting" value={brew.grind_setting_display ?? fmt(brew.grind_setting)} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Temperature" value={fmt(brew.temperature, '°C')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Pressure" value={fmt(brew.pressure, 'bar')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Flow Rate" value={fmt(brew.flow_rate, 'ml/s')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Pre-infusion Time" value={fmt(brew.pre_infusion_time, 's')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Total Time" value={fmt(brew.total_time, 's')} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <InfoRow label="Stop Mode" value={brew.stop_mode?.name} />
              </Grid>
            </Grid>
          </Grid>

          {/* Notes */}
          {brew.notes && (
            <Grid size={{ xs: 12 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Notes
              </Typography>
              <Typography variant="body2" whiteSpace="pre-wrap">{brew.notes}</Typography>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
}

// ─── TasteSlider ─────────────────────────────────────────────────────────────

function TasteSlider({
  label, name, value, onChange,
}: {
  label: string;
  name: string;
  value: number;
  onChange: (name: string, v: number) => void;
}) {
  return (
    <Stack spacing={0.5}>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2" color="text.secondary">{value}</Typography>
      </Stack>
      <Slider
        value={value}
        min={0}
        max={10}
        step={0.5}
        onChange={(_, v) => onChange(name, v as number)}
        size="small"
      />
    </Stack>
  );
}

// ─── TasteFormDialog ─────────────────────────────────────────────────────────

interface TasteFormState {
  score: number;
  acidity: number;
  sweetness: number;
  body: number;
  bitterness: number;
  balance: number;
  aftertaste: number;
  notes: string;
  flavor_tags: { id: string; name: string }[];
}

function defaultTasteForm(taste?: BrewTaste | null): TasteFormState {
  return {
    score: taste?.score ?? 7,
    acidity: taste?.acidity ?? 5,
    sweetness: taste?.sweetness ?? 5,
    body: taste?.body ?? 5,
    bitterness: taste?.bitterness ?? 5,
    balance: taste?.balance ?? 5,
    aftertaste: taste?.aftertaste ?? 5,
    notes: taste?.notes ?? '',
    flavor_tags: taste?.flavor_tags ?? [],
  };
}

const TASTE_AXES = [
  { name: 'acidity', label: 'Acidity' },
  { name: 'sweetness', label: 'Sweetness' },
  { name: 'body', label: 'Body' },
  { name: 'bitterness', label: 'Bitterness' },
  { name: 'balance', label: 'Balance' },
  { name: 'aftertaste', label: 'Aftertaste' },
] as const;

function TasteFormDialog({
  open,
  brewId,
  existingTaste,
  onClose,
}: {
  open: boolean;
  brewId: string;
  existingTaste?: BrewTaste | null;
  onClose: () => void;
}) {
  const [form, setForm] = useState<TasteFormState>(() => defaultTasteForm(existingTaste));
  const upsertTaste = useUpsertBrewTaste(brewId);
  const { notify } = useNotification();

  // reset form when dialog opens
  const handleOpen = () => setForm(defaultTasteForm(existingTaste));

  const handleSlider = (name: string, v: number) =>
    setForm((prev) => ({ ...prev, [name]: v }));

  const handleSubmit = async () => {
    await upsertTaste.mutateAsync({
      score: form.score,
      acidity: form.acidity,
      sweetness: form.sweetness,
      body: form.body,
      bitterness: form.bitterness,
      balance: form.balance,
      aftertaste: form.aftertaste,
      notes: form.notes || null,
      flavor_tag_ids: form.flavor_tags.map((t) => t.id),
    });
    notify(existingTaste ? 'Taste updated' : 'Taste added');
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      TransitionProps={{ onEnter: handleOpen }}
    >
      <DialogTitle>{existingTaste ? 'Edit Taste' : 'Add Taste'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {/* Score */}
          <Stack spacing={0.5}>
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="body2" fontWeight="medium">Score</Typography>
              <Typography variant="body2" color="text.secondary">{form.score}</Typography>
            </Stack>
            <Slider
              value={form.score}
              min={0}
              max={10}
              step={0.5}
              onChange={(_, v) => handleSlider('score', v as number)}
              size="small"
              color="secondary"
            />
          </Stack>

          <Divider />

          {/* Axes */}
          {TASTE_AXES.map(({ name, label }) => (
            <TasteSlider
              key={name}
              label={label}
              name={name}
              value={form[name]}
              onChange={handleSlider}
            />
          ))}

          <Divider />

          {/* Flavor tags */}
          <FlavorTagSelect
            value={form.flavor_tags}
            onChange={(tags) => setForm((prev) => ({ ...prev, flavor_tags: tags }))}
          />

          {/* Notes */}
          <TextField
            label="Notes"
            multiline
            minRows={2}
            value={form.notes}
            onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={upsertTaste.isPending}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ─── TasteSection ─────────────────────────────────────────────────────────────

function TasteSection({ brew }: { brew: Brew }) {
  const [tasteFormOpen, setTasteFormOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const deleteTaste = useDeleteBrewTaste(brew.id);
  const { notify } = useNotification();

  const handleDeleteTaste = async () => {
    await deleteTaste.mutateAsync();
    notify('Taste deleted');
    setDeleteConfirmOpen(false);
  };

  const taste = brew.taste;

  return (
    <>
      <Card variant="outlined" sx={{ mt: 3 }}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">Taste</Typography>
            <Stack direction="row" spacing={1}>
              {taste ? (
                <>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<EditIcon />}
                    onClick={() => setTasteFormOpen(true)}
                  >
                    Edit Taste
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => setDeleteConfirmOpen(true)}
                  >
                    Delete Taste
                  </Button>
                </>
              ) : (
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => setTasteFormOpen(true)}
                >
                  Add Taste
                </Button>
              )}
            </Stack>
          </Stack>

          {taste ? (
            <Grid container spacing={3}>
              {/* Score + axes */}
              <Grid size={{ xs: 12, md: 5 }}>
                {/* Score hero */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">Score</Typography>
                  <Typography variant="h3" fontWeight="bold" color="primary">
                    {taste.score != null ? taste.score.toFixed(1) : '—'}
                  </Typography>
                </Box>

                <Divider sx={{ mb: 1.5 }} />

                {/* Axes values */}
                <Stack spacing={0.5}>
                  {TASTE_AXES.map(({ name, label }) => (
                    <Stack key={name} direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">{label}</Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {taste[name] != null ? taste[name] : '—'}
                      </Typography>
                    </Stack>
                  ))}
                </Stack>
              </Grid>

              {/* Radar */}
              <Grid size={{ xs: 12, md: 7 }}>
                <TasteRadar data={brewTasteToRadar(taste)} size={280} />
              </Grid>

              {/* Flavor tags */}
              {taste.flavor_tags.length > 0 && (
                <Grid size={{ xs: 12 }}>
                  <Divider sx={{ mb: 1.5 }} />
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Flavor Tags
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
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
                </Grid>
              )}

              {/* Notes */}
              {taste.notes && (
                <Grid size={{ xs: 12 }}>
                  <Divider sx={{ mb: 1.5 }} />
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Taste Notes
                  </Typography>
                  <Typography variant="body2" whiteSpace="pre-wrap">{taste.notes}</Typography>
                </Grid>
              )}
            </Grid>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No taste recorded yet. Add taste data to track this brew's flavor profile.
            </Typography>
          )}
        </CardContent>
      </Card>

      <TasteFormDialog
        open={tasteFormOpen}
        brewId={brew.id}
        existingTaste={taste}
        onClose={() => setTasteFormOpen(false)}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Delete Taste"
        message="Delete the taste record for this brew? This cannot be undone."
        confirmLabel="Delete"
        variant="delete"
        onConfirm={handleDeleteTaste}
        onCancel={() => setDeleteConfirmOpen(false)}
      />
    </>
  );
}

// ─── EditBrewDialog ───────────────────────────────────────────────────────────

interface EditBrewForm {
  dose: string;
  yield_amount: string;
  grind_setting: string;
  temperature: string;
  pressure: string;
  flow_rate: string;
  pre_infusion_time: string;
  total_time: string;
  notes: string;
  is_failed: boolean;
}

function brewToEditForm(brew: Brew): EditBrewForm {
  return {
    dose: brew.dose != null ? String(brew.dose) : '',
    yield_amount: brew.yield_amount != null ? String(brew.yield_amount) : '',
    grind_setting: brew.grind_setting != null ? String(brew.grind_setting) : '',
    temperature: brew.temperature != null ? String(brew.temperature) : '',
    pressure: brew.pressure != null ? String(brew.pressure) : '',
    flow_rate: brew.flow_rate != null ? String(brew.flow_rate) : '',
    pre_infusion_time: brew.pre_infusion_time != null ? String(brew.pre_infusion_time) : '',
    total_time: brew.total_time != null ? String(brew.total_time) : '',
    notes: brew.notes ?? '',
    is_failed: brew.is_failed,
  };
}

function parseOptionalFloat(s: string): number | null {
  const v = parseFloat(s);
  return Number.isFinite(v) ? v : null;
}

function EditBrewDialog({
  open,
  brew,
  onClose,
}: {
  open: boolean;
  brew: Brew;
  onClose: () => void;
}) {
  const [form, setForm] = useState<EditBrewForm>(() => brewToEditForm(brew));
  const updateBrew = useUpdateBrew();
  const { notify } = useNotification();

  const handleOpen = () => setForm(brewToEditForm(brew));

  const set = (field: keyof EditBrewForm) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async () => {
    await updateBrew.mutateAsync({
      id: brew.id,
      dose: parseOptionalFloat(form.dose),
      yield_amount: parseOptionalFloat(form.yield_amount),
      grind_setting: parseOptionalFloat(form.grind_setting),
      temperature: parseOptionalFloat(form.temperature),
      pressure: parseOptionalFloat(form.pressure),
      flow_rate: parseOptionalFloat(form.flow_rate),
      pre_infusion_time: parseOptionalFloat(form.pre_infusion_time),
      total_time: parseOptionalFloat(form.total_time),
      notes: form.notes || null,
      is_failed: form.is_failed,
    });
    notify('Brew updated');
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      TransitionProps={{ onEnter: handleOpen }}
    >
      <DialogTitle>Edit Brew</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 6 }}>
              <TextField label="Dose (g)" value={form.dose} onChange={set('dose')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Yield (g)" value={form.yield_amount} onChange={set('yield_amount')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Grind Setting" value={form.grind_setting} onChange={set('grind_setting')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Temperature (°C)" value={form.temperature} onChange={set('temperature')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Pressure (bar)" value={form.pressure} onChange={set('pressure')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Flow Rate (ml/s)" value={form.flow_rate} onChange={set('flow_rate')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Pre-infusion Time (s)" value={form.pre_infusion_time} onChange={set('pre_infusion_time')} type="number" fullWidth />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField label="Total Time (s)" value={form.total_time} onChange={set('total_time')} type="number" fullWidth />
            </Grid>
          </Grid>

          <TextField
            label="Notes"
            multiline
            minRows={2}
            value={form.notes}
            onChange={set('notes')}
            fullWidth
          />

          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">Mark as Failed</Typography>
            <Chip
              label={form.is_failed ? 'Failed' : 'Success'}
              color={form.is_failed ? 'error' : 'success'}
              size="small"
              onClick={() => setForm((prev) => ({ ...prev, is_failed: !prev.is_failed }))}
              clickable
            />
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={updateBrew.isPending}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ─── BrewDetailPage ───────────────────────────────────────────────────────────

export default function BrewDetailPage() {
  const { brewId } = useParams<{ brewId: string }>();
  const { data: brew, isLoading } = useBrew(brewId ?? '');
  const deleteBrew = useDeleteBrew();
  const { notify } = useNotification();

  const [editOpen, setEditOpen] = useState(false);
  const [retireOpen, setRetireOpen] = useState(false);

  const handleRetire = async () => {
    if (brew) {
      await deleteBrew.mutateAsync(brew.id);
      notify('Brew retired');
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

  if (!brew) {
    return <Typography>Brew not found.</Typography>;
  }

  const brewLabel = brew.bag?.bean_name
    ? `${brew.bag.bean_name} — ${new Date(brew.brewed_at).toLocaleDateString()}`
    : new Date(brew.brewed_at).toLocaleDateString();

  return (
    <>
      <PageHeader
        title="Brew"
        breadcrumbs={[
          { label: 'Brews', to: '/brews' },
          { label: brewLabel },
        ]}
        actions={
          <>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => setEditOpen(true)}
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

      <BrewInfoCard brew={brew} />

      <TasteSection brew={brew} />

      <EditBrewDialog
        open={editOpen}
        brew={brew}
        onClose={() => setEditOpen(false)}
      />

      <ConfirmDialog
        open={retireOpen}
        title="Retire Brew"
        message={`Retire this brew from ${brew.bag?.bean_name ?? 'unknown bean'}? It will be hidden but not deleted.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireOpen(false)}
      />
    </>
  );
}
