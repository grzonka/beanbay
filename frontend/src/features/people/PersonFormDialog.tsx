import { useState, useEffect } from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Switch, FormControlLabel, TextField } from '@mui/material';
import { useCreatePerson, useUpdatePerson, type Person } from './hooks';
import { useNotification } from '@/components/NotificationProvider';

interface PersonFormDialogProps {
  open: boolean;
  onClose: () => void;
  person?: Person | null;
}

export default function PersonFormDialog({ open, onClose, person }: PersonFormDialogProps) {
  const [name, setName] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const isEdit = !!person;
  const create = useCreatePerson();
  const update = useUpdatePerson();
  const { notify } = useNotification();

  useEffect(() => {
    if (person) { setName(person.name); setIsDefault(person.is_default); }
    else { setName(''); setIsDefault(false); }
  }, [person, open]);

  const handleSubmit = async () => {
    if (isEdit) {
      await update.mutateAsync({ id: person!.id, name, is_default: isDefault });
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
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          {isEdit && (
            <FormControlLabel control={<Switch checked={isDefault} onChange={(_, c) => setIsDefault(c)} />} label="Default person" />
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!name.trim()}>{isEdit ? 'Save' : 'Create'}</Button>
      </DialogActions>
    </Dialog>
  );
}
