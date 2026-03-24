import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import FlavorTagSelect from '@/components/FlavorTagSelect';
import { useNotification } from '@/components/NotificationProvider';
import { Delete as DeleteIcon } from '@mui/icons-material';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import {
  type Bean,
  type FlavorTag,
  useCreateBean,
  useUpdateBean,
} from '../hooks';

interface OptionItem {
  id: string;
  name: string;
}

interface OriginWithPercentage {
  origin: OptionItem;
  percentage: string;
}

interface BeanFormDialogProps {
  open: boolean;
  onClose: () => void;
  bean?: Bean | null;
  onCreated?: (bean: Bean) => void;
}

function CreateInlineForm({
  endpoint,
  label,
  fields,
  initialName,
  onCreated,
  onCancel,
}: {
  endpoint: string;
  label: string;
  fields?: Array<{ key: string; label: string }>;
  initialName: string;
  onCreated: (item: OptionItem) => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({
    name: initialName,
  });
  const { notify } = useNotification();

  const handleSubmit = async () => {
    const { data } = await apiClient.post<OptionItem>(`/${endpoint}`, values);
    notify(`${label} created`);
    onCreated(data);
  };

  return (
    <Stack spacing={2} sx={{ pt: 1 }}>
      <TextField
        label="Name"
        value={values.name ?? ''}
        onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
        required
        autoFocus
      />
      {fields?.map((f) => (
        <TextField
          key={f.key}
          label={f.label}
          value={values[f.key] ?? ''}
          onChange={(e) =>
            setValues((v) => ({ ...v, [f.key]: e.target.value }))
          }
        />
      ))}
      <Stack direction="row" spacing={1} justifyContent="flex-end">
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!values.name?.trim()}
        >
          Create
        </Button>
      </Stack>
    </Stack>
  );
}

export default function BeanFormDialog({
  open,
  onClose,
  bean,
  onCreated,
}: BeanFormDialogProps) {
  const isEdit = !!bean;
  const create = useCreateBean();
  const update = useUpdateBean();
  const { notify } = useNotification();

  // Form state
  const [name, setName] = useState('');
  const [roaster, setRoaster] = useState<OptionItem | null>(null);
  const [roastDegree, setRoastDegree] = useState<number>(5);
  const [beanMixType, setBeanMixType] = useState('unknown');
  const [beanUseType, setBeanUseType] = useState('omni');
  const [decaf, setDecaf] = useState(false);
  const [url, setUrl] = useState('');
  const [ean, setEan] = useState('');
  const [notes, setNotes] = useState('');
  const [origins, setOrigins] = useState<OriginWithPercentage[]>([]);
  const [processes, setProcesses] = useState<OptionItem[]>([]);
  const [varieties, setVarieties] = useState<OptionItem[]>([]);
  const [flavorTags, setFlavorTags] = useState<FlavorTag[]>([]);

  useEffect(() => {
    if (bean) {
      setName(bean.name);
      setRoaster(bean.roaster ?? null);
      setRoastDegree(bean.roast_degree ?? 5);
      setBeanMixType(bean.bean_mix_type ?? 'unknown');
      setBeanUseType(bean.bean_use_type ?? 'omni');
      setDecaf(bean.decaf);
      setUrl(bean.url ?? '');
      setEan(bean.ean ?? '');
      setNotes(bean.notes ?? '');
      setOrigins(
        bean.origins.map((o) => ({
          origin: { id: o.origin_id, name: o.origin_name },
          percentage: o.percentage != null ? String(o.percentage) : '',
        })),
      );
      setProcesses(bean.processes.map((p) => ({ id: p.id, name: p.name })));
      setVarieties(bean.varieties.map((v) => ({ id: v.id, name: v.name })));
      setFlavorTags(bean.flavor_tags.map((t) => ({ id: t.id, name: t.name })));
    } else {
      setName('');
      setRoaster(null);
      setRoastDegree(5);
      setBeanMixType('unknown');
      setBeanUseType('omni');
      setDecaf(false);
      setUrl('');
      setEan('');
      setNotes('');
      setOrigins([]);
      setProcesses([]);
      setVarieties([]);
      setFlavorTags([]);
    }
  }, [bean, open]);

  const handleOriginsChange = (selected: OptionItem | OptionItem[] | null) => {
    const arr = (
      Array.isArray(selected) ? selected : selected ? [selected] : []
    ) as OptionItem[];
    setOrigins((prev) => {
      const prevMap = new Map(prev.map((o) => [o.origin.id, o.percentage]));
      return arr.map((origin) => ({
        origin,
        percentage: prevMap.get(origin.id) ?? '',
      }));
    });
  };

  const updatePercentage = (originId: string, val: string) => {
    setOrigins((prev) =>
      prev.map((o) =>
        o.origin.id === originId ? { ...o, percentage: val } : o,
      ),
    );
  };

  const buildBody = () => ({
    name,
    roaster_id: roaster?.id ?? null,
    roast_degree: roastDegree,
    bean_mix_type: beanMixType,
    bean_use_type: beanUseType,
    decaf,
    url: url || null,
    ean: ean || null,
    notes: notes || null,
    origins: origins.map((o) => ({
      origin_id: o.origin.id,
      percentage: o.percentage ? Number(o.percentage) : null,
    })),
    process_ids: processes.map((p) => p.id),
    variety_ids: varieties.map((v) => v.id),
    flavor_tag_ids: flavorTags.map((t) => t.id),
  });

  const buildPatchBody = () => {
    if (!bean) return {};
    const full = buildBody();
    const patch: Record<string, unknown> = {};

    if (full.name !== bean.name) patch.name = full.name;
    if (full.roaster_id !== (bean.roaster_id ?? null))
      patch.roaster_id = full.roaster_id;
    if (full.roast_degree !== (bean.roast_degree ?? 5))
      patch.roast_degree = full.roast_degree;
    if (full.bean_mix_type !== (bean.bean_mix_type ?? 'unknown'))
      patch.bean_mix_type = full.bean_mix_type;
    if (full.bean_use_type !== (bean.bean_use_type ?? 'omni'))
      patch.bean_use_type = full.bean_use_type;
    if (full.decaf !== bean.decaf) patch.decaf = full.decaf;
    if (full.url !== (bean.url ?? null)) patch.url = full.url;
    if (full.ean !== (bean.ean ?? null)) patch.ean = full.ean;
    if (full.notes !== (bean.notes ?? null)) patch.notes = full.notes;

    // For M2M always send (server handles diff)
    patch.origins = full.origins;
    patch.process_ids = full.process_ids;
    patch.variety_ids = full.variety_ids;
    patch.flavor_tag_ids = full.flavor_tag_ids;

    return patch;
  };

  const handleSubmit = async () => {
    if (isEdit) {
      await update.mutateAsync({ id: bean?.id, ...buildPatchBody() });
      notify('Bean updated');
      onClose();
    } else {
      const newBean = await create.mutateAsync(buildBody());
      notify('Bean created');
      onClose();
      onCreated?.(newBean as Bean);
    }
  };

  const isPending = create.isPending || update.isPending;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Bean' : 'Add Bean'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />

          <AutocompleteCreate<OptionItem>
            label="Roaster"
            queryKey={['roasters']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/roasters', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={roaster}
            onChange={(v) => setRoaster(v as OptionItem | null)}
            renderCreateForm={(props) => (
              <CreateInlineForm
                endpoint="roasters"
                label="Roaster"
                {...props}
              />
            )}
          />

          <Box>
            <Typography gutterBottom>Roast Degree: {roastDegree}</Typography>
            <Slider
              value={roastDegree}
              onChange={(_, v) => setRoastDegree(v as number)}
              min={0}
              max={10}
              step={1}
              marks
              valueLabelDisplay="auto"
            />
          </Box>

          <FormControl fullWidth>
            <InputLabel>Mix Type</InputLabel>
            <Select
              value={beanMixType}
              label="Mix Type"
              onChange={(e) => setBeanMixType(e.target.value)}
            >
              <MenuItem value="single_origin">Single Origin</MenuItem>
              <MenuItem value="blend">Blend</MenuItem>
              <MenuItem value="unknown">Unknown</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Use Type</InputLabel>
            <Select
              value={beanUseType}
              label="Use Type"
              onChange={(e) => setBeanUseType(e.target.value)}
            >
              <MenuItem value="filter">Filter</MenuItem>
              <MenuItem value="espresso">Espresso</MenuItem>
              <MenuItem value="omni">Omni</MenuItem>
            </Select>
          </FormControl>

          <FormControlLabel
            control={
              <Switch checked={decaf} onChange={(_, c) => setDecaf(c)} />
            }
            label="Decaf"
          />

          <TextField
            label="URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <TextField
            label="EAN"
            value={ean}
            onChange={(e) => setEan(e.target.value)}
          />

          <AutocompleteCreate<OptionItem>
            label="Origins"
            queryKey={['origins']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/origins', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={origins.map((o) => o.origin)}
            onChange={handleOriginsChange}
            multiple
            renderCreateForm={(props) => (
              <CreateInlineForm
                endpoint="origins"
                label="Origin"
                fields={[
                  { key: 'country', label: 'Country' },
                  { key: 'region', label: 'Region' },
                ]}
                {...props}
              />
            )}
          />

          {origins.length > 0 && (
            <Stack spacing={1}>
              <Typography variant="caption" color="text.secondary">
                Origin Percentages (optional)
              </Typography>
              {origins.map((o) => (
                <Stack
                  key={o.origin.id}
                  direction="row"
                  spacing={1}
                  alignItems="center"
                >
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {o.origin.name}
                  </Typography>
                  <TextField
                    label="%"
                    size="small"
                    type="number"
                    value={o.percentage}
                    onChange={(e) =>
                      updatePercentage(o.origin.id, e.target.value)
                    }
                    sx={{ width: 90 }}
                    slotProps={{ input: { inputProps: { min: 0, max: 100 } } }}
                  />
                  <IconButton
                    size="small"
                    onClick={() =>
                      setOrigins((prev) =>
                        prev.filter((x) => x.origin.id !== o.origin.id),
                      )
                    }
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Stack>
              ))}
            </Stack>
          )}

          <AutocompleteCreate<OptionItem>
            label="Process Methods"
            queryKey={['process-methods']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/process-methods', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={processes}
            onChange={(v) => setProcesses((v ?? []) as OptionItem[])}
            multiple
            renderCreateForm={(props) => (
              <CreateInlineForm
                endpoint="process-methods"
                label="Process Method"
                fields={[{ key: 'category', label: 'Category' }]}
                {...props}
              />
            )}
          />

          <AutocompleteCreate<OptionItem>
            label="Varieties"
            queryKey={['bean-varieties']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/bean-varieties', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={varieties}
            onChange={(v) => setVarieties((v ?? []) as OptionItem[])}
            multiple
            renderCreateForm={(props) => (
              <CreateInlineForm
                endpoint="bean-varieties"
                label="Bean Variety"
                fields={[{ key: 'species', label: 'Species' }]}
                {...props}
              />
            )}
          />

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
          disabled={!name.trim() || isPending}
        >
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
