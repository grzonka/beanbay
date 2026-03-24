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
  Stack,
  TextField,
} from '@mui/material';
import { useEffect, useState } from 'react';
import {
  type BrewSetup,
  useCreateBrewSetup,
  useUpdateBrewSetup,
} from './hooks';

interface OptionType {
  id: string;
  name: string;
}

function makeCreateForm(endpoint: string, label: string) {
  return function CreateForm({
    initialName,
    onCreated,
    onCancel,
  }: {
    initialName: string;
    onCreated: (item: OptionType) => void;
    onCancel: () => void;
  }) {
    const [name, setName] = useState(initialName);
    const { notify } = useNotification();

    const handleSubmit = async () => {
      const { data } = await apiClient.post<OptionType>(endpoint, { name });
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
  };
}

const BrewMethodCreateForm = makeCreateForm('/brew-methods', 'Brew Method');
const GrinderCreateForm = makeCreateForm('/grinders', 'Grinder');
const BrewerCreateForm = makeCreateForm('/brewers', 'Brewer');
const PaperCreateForm = makeCreateForm('/papers', 'Paper');
const WaterCreateForm = makeCreateForm('/waters', 'Water');

interface BrewSetupFormDialogProps {
  open: boolean;
  onClose: () => void;
  brewSetup?: BrewSetup | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

export default function BrewSetupFormDialog({
  open,
  onClose,
  brewSetup,
  onRetire,
  onActivate,
}: BrewSetupFormDialogProps) {
  const isEdit = !!brewSetup;
  const create = useCreateBrewSetup();
  const update = useUpdateBrewSetup();
  const { notify } = useNotification();

  const [name, setName] = useState('');
  const [brewMethod, setBrewMethod] = useState<OptionType | null>(null);
  const [grinder, setGrinder] = useState<OptionType | null>(null);
  const [brewer, setBrewer] = useState<OptionType | null>(null);
  const [paper, setPaper] = useState<OptionType | null>(null);
  const [water, setWater] = useState<OptionType | null>(null);

  useEffect(() => {
    if (brewSetup) {
      setName(brewSetup.name ?? '');
      setBrewMethod(
        brewSetup.brew_method_id && brewSetup.brew_method_name
          ? { id: brewSetup.brew_method_id, name: brewSetup.brew_method_name }
          : null,
      );
      setGrinder(
        brewSetup.grinder_id && brewSetup.grinder_name
          ? { id: brewSetup.grinder_id, name: brewSetup.grinder_name }
          : null,
      );
      setBrewer(
        brewSetup.brewer_id && brewSetup.brewer_name
          ? { id: brewSetup.brewer_id, name: brewSetup.brewer_name }
          : null,
      );
      setPaper(
        brewSetup.paper_id && brewSetup.paper_name
          ? { id: brewSetup.paper_id, name: brewSetup.paper_name }
          : null,
      );
      setWater(
        brewSetup.water_id && brewSetup.water_name
          ? { id: brewSetup.water_id, name: brewSetup.water_name }
          : null,
      );
    } else {
      setName('');
      setBrewMethod(null);
      setGrinder(null);
      setBrewer(null);
      setPaper(null);
      setWater(null);
    }
  }, [brewSetup, open]);

  const handleSubmit = async () => {
    const body = {
      name: name.trim() || null,
      brew_method_id: brewMethod?.id ?? null,
      grinder_id: grinder?.id ?? null,
      brewer_id: brewer?.id ?? null,
      paper_id: paper?.id ?? null,
      water_id: water?.id ?? null,
    };
    if (isEdit) {
      await update.mutateAsync({ id: brewSetup?.id, ...body });
      notify('Brew setup updated');
    } else {
      await create.mutateAsync(body);
      notify('Brew setup created');
    }
    onClose();
  };

  const isValid = !!brewMethod;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Brew Setup' : 'Add Brew Setup'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Optional display name"
          />
          <AutocompleteCreate<OptionType>
            label="Brew Method"
            queryKey={['brew-methods']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/brew-methods', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={brewMethod}
            onChange={(v) => setBrewMethod(v as OptionType | null)}
            required
            error={!brewMethod}
            helperText={!brewMethod ? 'Brew method is required' : undefined}
            renderCreateForm={(props) => <BrewMethodCreateForm {...props} />}
          />
          <AutocompleteCreate<OptionType>
            label="Grinder"
            queryKey={['grinders']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/grinders', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={grinder}
            onChange={(v) => setGrinder(v as OptionType | null)}
            renderCreateForm={(props) => <GrinderCreateForm {...props} />}
          />
          <AutocompleteCreate<OptionType>
            label="Brewer"
            queryKey={['brewers']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/brewers', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={brewer}
            onChange={(v) => setBrewer(v as OptionType | null)}
            renderCreateForm={(props) => <BrewerCreateForm {...props} />}
          />
          <AutocompleteCreate<OptionType>
            label="Paper"
            queryKey={['papers']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/papers', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={paper}
            onChange={(v) => setPaper(v as OptionType | null)}
            renderCreateForm={(props) => <PaperCreateForm {...props} />}
          />
          <AutocompleteCreate<OptionType>
            label="Water"
            queryKey={['waters']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/waters', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={water}
            onChange={(v) => setWater(v as OptionType | null)}
            renderCreateForm={(props) => <WaterCreateForm {...props} />}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        {isEdit && brewSetup?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !brewSetup?.retired_at && onRetire && (
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
        <Button variant="contained" onClick={handleSubmit} disabled={!isValid}>
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
