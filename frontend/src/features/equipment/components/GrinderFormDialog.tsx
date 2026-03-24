import { useNotification } from '@/components/NotificationProvider';
import {
  Add as AddIcon,
  Archive as ArchiveIcon,
  Delete as DeleteIcon,
  RestoreFromTrash as RestoreFromTrashIcon,
} from '@mui/icons-material';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { type Grinder, type RingConfig, grinderHooks } from '../hooks';

interface GrinderFormDialogProps {
  open: boolean;
  onClose: () => void;
  grinder?: Grinder | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

const emptyRing = (): RingConfig => ({ label: '', min: 0, max: 100, step: 1 });

export default function GrinderFormDialog({
  open,
  onClose,
  grinder,
  onRetire,
  onActivate,
}: GrinderFormDialogProps) {
  const [name, setName] = useState('');
  const [dialType, setDialType] = useState('stepless');
  const [rings, setRings] = useState<RingConfig[]>([emptyRing()]);
  const isEdit = !!grinder;
  const create = grinderHooks.useCreate();
  const update = grinderHooks.useUpdate();
  const { notify } = useNotification();

  useEffect(() => {
    if (grinder) {
      setName(grinder.name);
      setDialType(grinder.dial_type ?? 'stepless');
      setRings(grinder.rings?.length ? grinder.rings : [emptyRing()]);
    } else {
      setName('');
      setDialType('stepless');
      setRings([emptyRing()]);
    }
  }, [grinder, open]);

  const handleAddRing = () => setRings((prev) => [...prev, emptyRing()]);

  const handleRemoveRing = (index: number) =>
    setRings((prev) => prev.filter((_, i) => i !== index));

  const handleRingChange = (
    index: number,
    field: keyof RingConfig,
    value: string | number,
  ) =>
    setRings((prev) =>
      prev.map((ring, i) => (i === index ? { ...ring, [field]: value } : ring)),
    );

  const handleSubmit = async () => {
    const body = {
      name,
      dial_type: dialType,
      rings,
    };
    if (isEdit) {
      await update.mutateAsync({ id: grinder?.id, ...body });
      notify('Grinder updated');
    } else {
      await create.mutateAsync(body);
      notify('Grinder created');
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Grinder' : 'Add Grinder'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
          <FormControl fullWidth>
            <InputLabel>Dial Type</InputLabel>
            <Select
              label="Dial Type"
              value={dialType}
              onChange={(e) => setDialType(e.target.value)}
            >
              <MenuItem value="stepless">Stepless</MenuItem>
              <MenuItem value="stepped">Stepped</MenuItem>
            </Select>
          </FormControl>
          <Stack spacing={1}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
            >
              <Typography variant="subtitle2">Ring Configurations</Typography>
              <IconButton
                size="small"
                onClick={handleAddRing}
                aria-label="Add ring"
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </Stack>
            {rings.map((ring, index) => (
              <Stack
                key={index}
                direction="row"
                spacing={1}
                alignItems="center"
              >
                <TextField
                  label="Label"
                  value={ring.label}
                  onChange={(e) =>
                    handleRingChange(index, 'label', e.target.value)
                  }
                  size="small"
                  sx={{ flex: 2 }}
                />
                <TextField
                  label="Min"
                  type="number"
                  value={ring.min}
                  onChange={(e) =>
                    handleRingChange(index, 'min', Number(e.target.value))
                  }
                  size="small"
                  sx={{ flex: 1 }}
                />
                <TextField
                  label="Max"
                  type="number"
                  value={ring.max}
                  onChange={(e) =>
                    handleRingChange(index, 'max', Number(e.target.value))
                  }
                  size="small"
                  sx={{ flex: 1 }}
                />
                <TextField
                  label="Step"
                  type="number"
                  value={ring.step}
                  onChange={(e) =>
                    handleRingChange(index, 'step', Number(e.target.value))
                  }
                  size="small"
                  sx={{ flex: 1 }}
                />
                <IconButton
                  size="small"
                  onClick={() => handleRemoveRing(index)}
                  aria-label="Remove ring"
                  disabled={rings.length === 1}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        {isEdit && grinder?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !grinder?.retired_at && onRetire && (
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
