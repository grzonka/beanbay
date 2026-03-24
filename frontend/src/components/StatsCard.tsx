// frontend/src/components/StatsCard.tsx
import {
  Card,
  CardContent,
  Skeleton,
  type SxProps,
  Typography,
} from '@mui/material';
import type { ReactNode } from 'react';

interface StatsCardProps {
  label: string;
  value: string | number | null | undefined;
  icon?: ReactNode;
  loading?: boolean;
  sx?: SxProps;
}

export default function StatsCard({
  label,
  value,
  icon,
  loading,
  sx,
}: StatsCardProps) {
  return (
    <Card sx={{ minWidth: 140, ...sx }}>
      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {icon && <div style={{ fontSize: 32, opacity: 0.7 }}>{icon}</div>}
        <div>
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
          {loading ? (
            <Skeleton width={60} height={32} />
          ) : (
            <Typography variant="h5" component="div">
              {value ?? '—'}
            </Typography>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
