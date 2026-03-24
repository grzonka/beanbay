// frontend/src/components/PageHeader.tsx
import { Box, Breadcrumbs, Link, Typography } from '@mui/material';
import type { ReactNode } from 'react';
import { Link as RouterLink } from 'react-router';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
}

export default function PageHeader({
  title,
  breadcrumbs,
  actions,
}: PageHeaderProps) {
  return (
    <Box sx={{ mb: 3 }}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumbs sx={{ mb: 1 }}>
          {breadcrumbs.map((bc) =>
            bc.to ? (
              <Link
                key={bc.label}
                component={RouterLink}
                to={bc.to}
                underline="hover"
                color="inherit"
              >
                {bc.label}
              </Link>
            ) : (
              <Typography key={bc.label} color="text.primary">
                {bc.label}
              </Typography>
            ),
          )}
        </Breadcrumbs>
      )}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
        }}
      >
        <Typography variant="h4" component="h1">
          {title}
        </Typography>
        {actions && <Box sx={{ display: 'flex', gap: 1 }}>{actions}</Box>}
      </Box>
    </Box>
  );
}
