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
import { type Paper, paperHooks } from '../hooks';

interface PaperFormDialogProps {
  open: boolean;
  onClose: () => void;
  paper?: Paper | null;
  onRetire?: () => void;
  onActivate?: () => void;
}

export default function PaperFormDialog({
  open,
  onClose,
  paper,
  onRetire,
  onActivate,
}: PaperFormDialogProps) {
  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const isEdit = !!paper;
  const create = paperHooks.useCreate();
  const update = paperHooks.useUpdate();
  const { notify } = useNotification();

  useEffect(() => {
    if (paper) {
      setName(paper.name);
      setNotes(paper.notes ?? '');
    } else {
      setName('');
      setNotes('');
    }
  }, [paper, open]);

  const handleSubmit = async () => {
    if (isEdit) {
      await update.mutateAsync({ id: paper?.id, name, notes: notes || null });
      notify('Paper updated');
    } else {
      await create.mutateAsync({ name, notes: notes || null });
      notify('Paper created');
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{isEdit ? 'Edit Paper' : 'Add Paper'}</DialogTitle>
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
        </Stack>
      </DialogContent>
      <DialogActions>
        {isEdit && paper?.retired_at && onActivate && (
          <Button
            color="success"
            onClick={onActivate}
            sx={{ mr: 'auto' }}
            startIcon={<RestoreFromTrashIcon />}
          >
            Activate
          </Button>
        )}
        {isEdit && !paper?.retired_at && onRetire && (
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
