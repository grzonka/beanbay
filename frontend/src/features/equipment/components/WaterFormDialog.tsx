import { useNotification } from '@/components/NotificationProvider';
import {
  Add as AddIcon,
  Archive as ArchiveIcon,
  Delete as DeleteIcon,
  RestoreFromTrash as RestoreFromTrashIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { type Water, waterHooks } from '../hooks';

interface MineralRow {
  mineral_name: string;
  ppm: number | '';
}

interface WaterFormDialogProps {
  open: boolean;
  onClose: () => void;
  water?: Water | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

export default function WaterFormDialog({
  open,
  onClose,
  water,
  onRetire,
  onActivate,
}: WaterFormDialogProps) {
  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const [minerals, setMinerals] = useState<MineralRow[]>([]);
  const isEdit = !!water;
  const create = waterHooks.useCreate();
  const update = waterHooks.useUpdate();
  const { notify } = useNotification();

  useEffect(() => {
    if (water) {
      setName(water.name);
      setNotes(water.notes ?? '');
      setMinerals(
        water.minerals.map((m) => ({
          mineral_name: m.mineral_name,
          ppm: m.ppm,
        })),
      );
    } else {
      setName('');
      setNotes('');
      setMinerals([]);
    }
  }, [water, open]);

  const addMineral = () => {
    setMinerals((prev) => [...prev, { mineral_name: '', ppm: '' }]);
  };

  const removeMineral = (index: number) => {
    setMinerals((prev) => prev.filter((_, i) => i !== index));
  };

  const updateMineral = (
    index: number,
    field: keyof MineralRow,
    value: string,
  ) => {
    setMinerals((prev) =>
      prev.map((m, i) => {
        if (i !== index) return m;
        if (field === 'ppm') {
          return { ...m, ppm: value === '' ? '' : Number(value) };
        }
        return { ...m, [field]: value };
      }),
    );
  };

  const handleSubmit = async () => {
    const validMinerals = minerals
      .filter((m) => m.mineral_name.trim() && m.ppm !== '')
      .map((m) => ({
        mineral_name: m.mineral_name.trim(),
        ppm: Number(m.ppm),
      }));

    if (isEdit) {
      await update.mutateAsync({
        id: water?.id,
        name,
        notes: notes || null,
        minerals: validMinerals,
      });
      notify('Water updated');
    } else {
      await create.mutateAsync({
        name,
        notes: notes || null,
        minerals: validMinerals,
      });
      notify('Water created');
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{isEdit ? 'Edit Water' : 'Add Water'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
          <TextField
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            rows={3}
          />

          <Box>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                mb: 1,
              }}
            >
              <Typography variant="subtitle2">Minerals</Typography>
              <IconButton
                size="small"
                onClick={addMineral}
                color="primary"
                aria-label="Add mineral"
              >
                <AddIcon />
              </IconButton>
            </Box>
            <Stack spacing={1}>
              {minerals.map((mineral, index) => (
                <Box
                  key={index}
                  sx={{ display: 'flex', gap: 1, alignItems: 'center' }}
                >
                  <TextField
                    label="Mineral"
                    value={mineral.mineral_name}
                    onChange={(e) =>
                      updateMineral(index, 'mineral_name', e.target.value)
                    }
                    size="small"
                    sx={{ flex: 2 }}
                  />
                  <TextField
                    label="PPM"
                    type="number"
                    value={mineral.ppm}
                    onChange={(e) =>
                      updateMineral(index, 'ppm', e.target.value)
                    }
                    size="small"
                    sx={{ flex: 1 }}
                    slotProps={{ htmlInput: { min: 0, step: 0.1 } }}
                  />
                  <IconButton
                    size="small"
                    onClick={() => removeMineral(index)}
                    aria-label="Remove mineral"
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              ))}
              {minerals.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  No minerals added. Click + to add one.
                </Typography>
              )}
            </Stack>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        {isEdit && water?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !water?.retired_at && onRetire && (
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
          disabled={!name.trim()}
        >
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
