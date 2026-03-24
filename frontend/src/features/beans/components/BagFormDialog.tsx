import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import { useNotification } from '@/components/NotificationProvider';
import {
  Archive as ArchiveIcon,
  RestoreFromTrash as RestoreFromTrashIcon,
} from '@mui/icons-material';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { type Bag, useCreateBag, useUpdateBag } from '../hooks';

interface OptionItem {
  id: string;
  name: string;
}

interface BagFormDialogProps {
  open: boolean;
  onClose: () => void;
  beanId: string;
  bag?: Bag | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

function CreateInlineForm({
  endpoint,
  label,
  initialName,
  onCreated,
  onCancel,
}: {
  endpoint: string;
  label: string;
  initialName: string;
  onCreated: (item: OptionItem) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initialName);
  const { notify } = useNotification();

  const handleSubmit = async () => {
    const { data } = await apiClient.post<OptionItem>(`/${endpoint}`, { name });
    notify(`${label} created`);
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

export default function BagFormDialog({
  open,
  onClose,
  beanId,
  bag,
  onRetire,
  onActivate,
}: BagFormDialogProps) {
  const isEdit = !!bag;
  const createBag = useCreateBag(beanId);
  const updateBag = useUpdateBag(beanId);
  const { notify } = useNotification();

  const [weight, setWeight] = useState('');
  const [price, setPrice] = useState('');
  const [roastDate, setRoastDate] = useState('');
  const [openedAt, setOpenedAt] = useState('');
  const [boughtAt, setBoughtAt] = useState('');
  const [bestDate, setBestDate] = useState('');
  const [frozenAt, setFrozenAt] = useState('');
  const [thawedAt, setThawedAt] = useState('');
  const [isPreground, setIsPreground] = useState(false);
  const [notes, setNotes] = useState('');
  const [vendor, setVendor] = useState<OptionItem | null>(null);
  const [storageType, setStorageType] = useState<OptionItem | null>(null);

  useEffect(() => {
    if (bag) {
      setWeight(bag.weight != null ? String(bag.weight) : '');
      setPrice(bag.price != null ? String(bag.price) : '');
      setRoastDate(bag.roast_date ?? '');
      setOpenedAt(bag.opened_at ?? '');
      setBoughtAt(bag.bought_at ?? '');
      setBestDate(bag.best_date ?? '');
      setFrozenAt(bag.frozen_at ?? '');
      setThawedAt(bag.thawed_at ?? '');
      setIsPreground(bag.is_preground);
      setNotes(bag.notes ?? '');
      setVendor(bag.vendor_id ? { id: bag.vendor_id, name: '' } : null);
      setStorageType(
        bag.storage_type_id ? { id: bag.storage_type_id, name: '' } : null,
      );
    } else {
      setWeight('');
      setPrice('');
      setRoastDate('');
      setOpenedAt('');
      setBoughtAt('');
      setBestDate('');
      setFrozenAt('');
      setThawedAt('');
      setIsPreground(false);
      setNotes('');
      setVendor(null);
      setStorageType(null);
    }
  }, [bag, open]);

  const buildBody = () => ({
    weight: weight ? Number(weight) : null,
    price: price ? Number(price) : null,
    roast_date: roastDate || null,
    opened_at: openedAt || null,
    bought_at: boughtAt || null,
    best_date: bestDate || null,
    frozen_at: frozenAt || null,
    thawed_at: thawedAt || null,
    is_preground: isPreground,
    notes: notes || null,
    vendor_id: vendor?.id ?? null,
    storage_type_id: storageType?.id ?? null,
  });

  const handleSubmit = async () => {
    const body = buildBody();
    if (isEdit) {
      await updateBag.mutateAsync({ id: bag?.id, ...body });
      notify('Bag updated');
    } else {
      await createBag.mutateAsync(body);
      notify('Bag added');
    }
    onClose();
  };

  const isPending = createBag.isPending || updateBag.isPending;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Bag' : 'Add Bag'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Weight (g)"
            type="number"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            required
            autoFocus
            slotProps={{ input: { inputProps: { min: 0 } } }}
          />

          <TextField
            label="Price"
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            slotProps={{ input: { inputProps: { min: 0, step: 0.01 } } }}
          />

          <TextField
            label="Roast Date"
            type="date"
            value={roastDate}
            onChange={(e) => setRoastDate(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <TextField
            label="Opened At"
            type="date"
            value={openedAt}
            onChange={(e) => setOpenedAt(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <TextField
            label="Bought At"
            type="date"
            value={boughtAt}
            onChange={(e) => setBoughtAt(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <TextField
            label="Best Before"
            type="date"
            value={bestDate}
            onChange={(e) => setBestDate(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <AutocompleteCreate<OptionItem>
            label="Vendor"
            queryKey={['vendors']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/vendors', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={vendor}
            onChange={(v) => setVendor(v as OptionItem | null)}
            renderCreateForm={(props) => (
              <CreateInlineForm endpoint="vendors" label="Vendor" {...props} />
            )}
          />

          <AutocompleteCreate<OptionItem>
            label="Storage Type"
            queryKey={['storage-types']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/storage-types', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={storageType}
            onChange={(v) => setStorageType(v as OptionItem | null)}
            renderCreateForm={(props) => (
              <CreateInlineForm
                endpoint="storage-types"
                label="Storage Type"
                {...props}
              />
            )}
          />

          <FormControlLabel
            control={
              <Switch
                checked={isPreground}
                onChange={(_, c) => setIsPreground(c)}
              />
            }
            label="Pre-ground"
          />

          <TextField
            label="Frozen At"
            type="datetime-local"
            value={frozenAt}
            onChange={(e) => setFrozenAt(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <TextField
            label="Thawed At"
            type="datetime-local"
            value={thawedAt}
            onChange={(e) => setThawedAt(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />

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
        {isEdit && bag?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            disabled={isPending}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !bag?.retired_at && onRetire && (
          <Button
            color="warning"
            onClick={onRetire}
            disabled={isPending}
            sx={{ mr: 'auto' }}
            startIcon={<ArchiveIcon />}
          >
            Retire
          </Button>
        )}
        <Button onClick={onClose} disabled={isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!weight || isPending}
        >
          {isEdit ? 'Save' : 'Add'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
