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
import { type Person, useCreatePerson, useUpdatePerson } from './hooks';

interface PersonFormDialogProps {
  open: boolean;
  onClose: () => void;
  person?: Person | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

export default function PersonFormDialog({
  open,
  onClose,
  person,
  onRetire,
  onActivate,
}: PersonFormDialogProps) {
  const [name, setName] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const isEdit = !!person;
  const create = useCreatePerson();
  const update = useUpdatePerson();
  const { notify } = useNotification();

  useEffect(() => {
    if (person) {
      setName(person.name);
      setIsDefault(person.is_default);
    } else {
      setName('');
      setIsDefault(false);
    }
  }, [person, open]);

  const handleSubmit = async () => {
    if (isEdit) {
      await update.mutateAsync({ id: person?.id, name, is_default: isDefault });
      notify('Person updated');
    } else {
      await create.mutateAsync({ name });
      notify('Person created');
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{isEdit ? 'Edit Person' : 'Add Person'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
          {isEdit && (
            <FormControlLabel
              control={
                <Switch
                  checked={isDefault}
                  onChange={(_, c) => setIsDefault(c)}
                />
              }
              label="Default person"
            />
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        {isEdit && person?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !person?.retired_at && onRetire && (
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
