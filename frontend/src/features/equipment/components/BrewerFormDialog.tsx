import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import { useNotification } from '@/components/NotificationProvider';
import {
  Archive as ArchiveIcon,
  ExpandMore as ExpandMoreIcon,
  RestoreFromTrash as RestoreFromTrashIcon,
} from '@mui/icons-material';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { type Brewer, brewerHooks } from '../hooks';

interface BrewerFormDialogProps {
  open: boolean;
  onClose: () => void;
  brewer?: Brewer | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

interface NamedItem {
  id: string;
  name: string;
}

const defaultForm = () => ({
  name: '',
  temp_control_type: 'none' as string,
  temp_min: '' as string | number,
  temp_max: '' as string | number,
  temp_step: '' as string | number,
  preinfusion_type: 'none' as string,
  preinfusion_max_time: '' as string | number,
  pressure_control_type: 'fixed' as string,
  pressure_min: '' as string | number,
  pressure_max: '' as string | number,
  flow_control_type: 'none' as string,
  saturation_flow_rate: '' as string | number,
  has_bloom: false,
  methods: [] as NamedItem[],
  stop_modes: [] as NamedItem[],
});

type FormState = ReturnType<typeof defaultForm>;

function numOrNull(val: string | number): number | null {
  if (val === '' || val === null || val === undefined) return null;
  const n = Number(val);
  return Number.isNaN(n) ? null : n;
}

async function fetchBrewMethods(q: string): Promise<{ items: NamedItem[] }> {
  const { data } = await apiClient.get('/brew-methods', {
    params: { q, limit: 50 },
  });
  return data;
}

async function fetchStopModes(q: string): Promise<{ items: NamedItem[] }> {
  const { data } = await apiClient.get('/stop-modes', {
    params: { q, limit: 50 },
  });
  return data;
}

export default function BrewerFormDialog({
  open,
  onClose,
  brewer,
  onRetire,
  onActivate,
}: BrewerFormDialogProps) {
  const [form, setForm] = useState<FormState>(defaultForm());
  const isEdit = !!brewer;
  const create = brewerHooks.useCreate();
  const update = brewerHooks.useUpdate();
  const { notify } = useNotification();

  useEffect(() => {
    if (open) {
      if (brewer) {
        setForm({
          name: brewer.name,
          temp_control_type: brewer.temp_control_type ?? 'none',
          temp_min: brewer.temp_min ?? '',
          temp_max: brewer.temp_max ?? '',
          temp_step: brewer.temp_step ?? '',
          preinfusion_type: brewer.preinfusion_type ?? 'none',
          preinfusion_max_time: brewer.preinfusion_max_time ?? '',
          pressure_control_type: brewer.pressure_control_type ?? 'fixed',
          pressure_min: brewer.pressure_min ?? '',
          pressure_max: brewer.pressure_max ?? '',
          flow_control_type: brewer.flow_control_type ?? 'none',
          saturation_flow_rate: brewer.saturation_flow_rate ?? '',
          has_bloom: brewer.has_bloom ?? false,
          methods: brewer.methods ?? [],
          stop_modes: brewer.stop_modes ?? [],
        });
      } else {
        setForm(defaultForm());
      }
    }
  }, [brewer, open]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    const body = {
      name: form.name,
      temp_control_type: form.temp_control_type,
      temp_min:
        form.temp_control_type !== 'none' ? numOrNull(form.temp_min) : null,
      temp_max:
        form.temp_control_type !== 'none' ? numOrNull(form.temp_max) : null,
      temp_step:
        form.temp_control_type !== 'none' ? numOrNull(form.temp_step) : null,
      preinfusion_type: form.preinfusion_type,
      preinfusion_max_time:
        form.preinfusion_type !== 'none'
          ? numOrNull(form.preinfusion_max_time)
          : null,
      pressure_control_type: form.pressure_control_type,
      pressure_min: numOrNull(form.pressure_min),
      pressure_max: numOrNull(form.pressure_max),
      flow_control_type: form.flow_control_type,
      saturation_flow_rate:
        form.flow_control_type !== 'none'
          ? numOrNull(form.saturation_flow_rate)
          : null,
      has_bloom: form.has_bloom,
      method_ids: form.methods.map((m) => m.id),
      stop_mode_ids: form.stop_modes.map((s) => s.id),
    };
    if (isEdit) {
      await update.mutateAsync({ id: brewer?.id, ...body });
      notify('Brewer updated');
    } else {
      await create.mutateAsync(body);
      notify('Brewer created');
    }
    onClose();
  };

  const showTempFields = form.temp_control_type !== 'none';
  const showPreinfusionTime = form.preinfusion_type !== 'none';
  const showFlowRate = form.flow_control_type !== 'none';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Brewer' : 'Add Brewer'}</DialogTitle>
      <DialogContent sx={{ px: 2, py: 1 }}>
        {/* Basic */}
        <Accordion
          defaultExpanded
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Basic</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TextField
              label="Name"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              required
              autoFocus
              fullWidth
            />
          </AccordionDetails>
        </Accordion>

        {/* Temperature */}
        <Accordion
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Temperature</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Temp Control Type</InputLabel>
                <Select
                  label="Temp Control Type"
                  value={form.temp_control_type}
                  onChange={(e) => set('temp_control_type', e.target.value)}
                >
                  <MenuItem value="none">None</MenuItem>
                  <MenuItem value="preset">Preset</MenuItem>
                  <MenuItem value="pid">PID</MenuItem>
                  <MenuItem value="profiling">Profiling</MenuItem>
                </Select>
              </FormControl>
              {showTempFields && (
                <Stack direction="row" spacing={2}>
                  <TextField
                    label="Min Temp"
                    type="number"
                    value={form.temp_min}
                    onChange={(e) => set('temp_min', e.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="Max Temp"
                    type="number"
                    value={form.temp_max}
                    onChange={(e) => set('temp_max', e.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="Temp Step"
                    type="number"
                    value={form.temp_step}
                    onChange={(e) => set('temp_step', e.target.value)}
                    fullWidth
                  />
                </Stack>
              )}
            </Stack>
          </AccordionDetails>
        </Accordion>

        {/* Pre-infusion */}
        <Accordion
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Pre-infusion</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Pre-infusion Type</InputLabel>
                <Select
                  label="Pre-infusion Type"
                  value={form.preinfusion_type}
                  onChange={(e) => set('preinfusion_type', e.target.value)}
                >
                  <MenuItem value="none">None</MenuItem>
                  <MenuItem value="fixed">Fixed</MenuItem>
                  <MenuItem value="timed">Timed</MenuItem>
                  <MenuItem value="adjustable_pressure">
                    Adjustable Pressure
                  </MenuItem>
                  <MenuItem value="programmable">Programmable</MenuItem>
                  <MenuItem value="manual">Manual</MenuItem>
                </Select>
              </FormControl>
              {showPreinfusionTime && (
                <TextField
                  label="Max Pre-infusion Time (s)"
                  type="number"
                  value={form.preinfusion_max_time}
                  onChange={(e) => set('preinfusion_max_time', e.target.value)}
                  fullWidth
                />
              )}
            </Stack>
          </AccordionDetails>
        </Accordion>

        {/* Pressure */}
        <Accordion
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Pressure</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Pressure Control Type</InputLabel>
                <Select
                  label="Pressure Control Type"
                  value={form.pressure_control_type}
                  onChange={(e) => set('pressure_control_type', e.target.value)}
                >
                  <MenuItem value="fixed">Fixed</MenuItem>
                  <MenuItem value="opv_adjustable">OPV Adjustable</MenuItem>
                  <MenuItem value="electronic">Electronic</MenuItem>
                  <MenuItem value="manual_profiling">Manual Profiling</MenuItem>
                  <MenuItem value="programmable">Programmable</MenuItem>
                </Select>
              </FormControl>
              <Stack direction="row" spacing={2}>
                <TextField
                  label="Min Pressure (bar)"
                  type="number"
                  value={form.pressure_min}
                  onChange={(e) => set('pressure_min', e.target.value)}
                  fullWidth
                />
                <TextField
                  label="Max Pressure (bar)"
                  type="number"
                  value={form.pressure_max}
                  onChange={(e) => set('pressure_max', e.target.value)}
                  fullWidth
                />
              </Stack>
            </Stack>
          </AccordionDetails>
        </Accordion>

        {/* Flow */}
        <Accordion
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Flow</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Flow Control Type</InputLabel>
                <Select
                  label="Flow Control Type"
                  value={form.flow_control_type}
                  onChange={(e) => set('flow_control_type', e.target.value)}
                >
                  <MenuItem value="none">None</MenuItem>
                  <MenuItem value="manual_paddle">Manual Paddle</MenuItem>
                  <MenuItem value="manual_valve">Manual Valve</MenuItem>
                  <MenuItem value="programmable">Programmable</MenuItem>
                </Select>
              </FormControl>
              {showFlowRate && (
                <TextField
                  label="Saturation Flow Rate (ml/s)"
                  type="number"
                  value={form.saturation_flow_rate}
                  onChange={(e) => set('saturation_flow_rate', e.target.value)}
                  fullWidth
                />
              )}
            </Stack>
          </AccordionDetails>
        </Accordion>

        {/* Features */}
        <Accordion
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Features</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <FormControlLabel
              control={
                <Switch
                  checked={form.has_bloom}
                  onChange={(_, checked) => set('has_bloom', checked)}
                />
              }
              label="Has Bloom"
            />
          </AccordionDetails>
        </Accordion>

        {/* Methods & Modes */}
        <Accordion
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Methods & Modes</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <AutocompleteCreate<NamedItem>
                label="Brew Methods"
                queryKey={['brew-methods']}
                fetchFn={fetchBrewMethods}
                value={form.methods}
                onChange={(val) => set('methods', (val as NamedItem[]) ?? [])}
                multiple
              />
              <AutocompleteCreate<NamedItem>
                label="Stop Modes"
                queryKey={['stop-modes']}
                fetchFn={fetchStopModes}
                value={form.stop_modes}
                onChange={(val) =>
                  set('stop_modes', (val as NamedItem[]) ?? [])
                }
                multiple
              />
            </Stack>
          </AccordionDetails>
        </Accordion>
      </DialogContent>
      <DialogActions>
        {isEdit && brewer?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !brewer?.retired_at && onRetire && (
          <Button
            color="warning"
            onClick={onRetire}
            sx={{ mr: 'auto' }}
            startIcon={<ArchiveIcon />}
          >
            Retire
          </Button>
        )}
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!form.name.trim()}
        >
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
