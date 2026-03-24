// frontend/src/components/EmptyState.tsx
import { Box, Button, Typography } from '@mui/material';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 8,
        gap: 2,
      }}
    >
      {icon && (
        <Box sx={{ fontSize: 64, color: 'text.secondary', opacity: 0.5 }}>
          {icon}
        </Box>
      )}
      <Typography variant="h6" color="text.secondary">
        {title}
      </Typography>
      {description && (
        <Typography color="text.secondary">{description}</Typography>
      )}
      {actionLabel && onAction && (
        <Button variant="contained" onClick={onAction} sx={{ mt: 1 }}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
