import DataTable from '@/components/DataTable';
import { usePagination } from '@/utils/pagination';
import { Box, Chip, Typography } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { type Recommendation, useCampaignRecommendations } from '../hooks';

const phaseColor: Record<string, 'info' | 'warning' | 'success'> = {
  random: 'info',
  learning: 'warning',
  optimizing: 'success',
};

interface Props {
  campaignId: string;
}

export default function RecommendationHistory({ campaignId }: Props) {
  const { data: recs, isLoading } = useCampaignRecommendations(campaignId);
  const {
    paginationModel,
    onPaginationModelChange,
    sortModel,
    onSortModelChange,
  } = usePagination({ field: 'created_at', sort: 'desc' });

  if (!recs || recs.length === 0)
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">No recommendations yet</Typography>
      </Box>
    );

  const paramKeys = Object.keys(recs[0]?.parameter_values ?? {}).slice(0, 4);

  const columns: GridColDef[] = [
    {
      field: 'index',
      headerName: '#',
      width: 60,
      renderCell: (params) => params.api.getAllRowIds().indexOf(params.id) + 1,
      sortable: false,
    },
    {
      field: 'phase',
      headerName: 'Phase',
      width: 110,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={phaseColor[params.value as string] ?? 'default'}
        />
      ),
    },
    ...paramKeys.map((key) => ({
      field: `param_${key}`,
      headerName: key.replace(/_/g, ' '),
      width: 120,
      valueGetter: (_: unknown, row: Recommendation) =>
        row.parameter_values[key] != null
          ? Number(row.parameter_values[key]).toFixed(1)
          : '—',
    })),
    {
      field: 'predicted_score',
      headerName: 'Predicted',
      width: 130,
      renderCell: (params) => {
        const row = params.row as Recommendation;
        if (row.predicted_score == null) return '—';
        const std =
          row.predicted_std != null ? ` ±${row.predicted_std.toFixed(1)}` : '';
        return `${row.predicted_score.toFixed(1)}${std}`;
      },
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => {
        const c =
          params.value === 'brewed'
            ? 'success'
            : params.value === 'skipped'
              ? 'default'
              : 'warning';
        return (
          <Chip
            label={params.value}
            size="small"
            color={c as 'success' | 'default' | 'warning'}
          />
        );
      },
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 160,
      valueFormatter: (value: string) => new Date(value).toLocaleDateString(),
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={recs}
      total={recs.length}
      loading={isLoading}
      paginationModel={paginationModel}
      onPaginationModelChange={onPaginationModelChange}
      sortModel={sortModel}
      onSortModelChange={onSortModelChange}
    />
  );
}
