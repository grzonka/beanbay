// frontend/src/components/ConfirmDialog.tsx
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: 'retire' | 'delete';
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  variant = 'retire',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onClose={onCancel}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          onClick={onConfirm}
          color={variant === 'delete' ? 'error' : 'warning'}
          variant="contained"
        >
          {confirmLabel ?? (variant === 'delete' ? 'Delete' : 'Retire')}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
