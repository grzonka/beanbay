import DataTable from '@/components/DataTable';
import { type BrewListItem, useBrews } from '@/features/brews/hooks';
import { usePagination } from '@/utils/pagination';
import { Box, Chip, Typography } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import type { EffectiveRange } from '../hooks';

interface Props {
  beanId: string;
  brewSetupId: string;
  effectiveRanges: EffectiveRange[];
}

/** Map from effective-range parameter names to BrewListItem field names. */
const PARAM_FIELDS: Record<string, keyof BrewListItem> = {
  temperature: 'temperature',
  dose: 'dose',
  yield_amount: 'yield_amount',
  grind_setting: 'grind_setting',
};

export default function BrewHistory({
  beanId,
  brewSetupId,
  effectiveRanges,
}: Props) {
  const {
    paginationModel,
    onPaginationModelChange,
    sortModel,
    onSortModelChange,
  } = usePagination({ field: 'brewed_at', sort: 'desc' });
  const { data, isLoading } = useBrews({
    bean_id: beanId,
    brew_setup_id: brewSetupId,
    limit: paginationModel.pageSize,
    offset: paginationModel.page * paginationModel.pageSize,
    sort_by: sortModel[0]?.field ?? 'brewed_at',
    sort_dir: sortModel[0]?.sort ?? 'desc',
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  if (!isLoading && items.length === 0)
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">No brews yet</Typography>
      </Box>
    );

  // Build param columns from effective ranges (only numeric params that map to brew fields)
  const paramCols: GridColDef[] = effectiveRanges
    .filter((r) => r.allowed_values == null && PARAM_FIELDS[r.parameter_name])
    .map((r) => ({
      field: PARAM_FIELDS[r.parameter_name] as string,
      headerName: r.parameter_name.replace(/_/g, ' '),
      width: 120,
      valueFormatter: (value: number | null) =>
        value != null ? value.toFixed(1) : '—',
    }));

  const columns: GridColDef[] = [
    {
      field: 'index',
      headerName: '#',
      width: 60,
      renderCell: (params) => {
        const page = paginationModel.page;
        const size = paginationModel.pageSize;
        return (
          total - (page * size + params.api.getAllRowIds().indexOf(params.id))
        );
      },
      sortable: false,
    },
    ...paramCols,
    {
      field: 'score',
      headerName: 'Score',
      width: 100,
      valueFormatter: (value: number | null) =>
        value != null ? value.toFixed(1) : '—',
    },
    {
      field: 'is_failed',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => {
        const failed = params.value as boolean;
        return (
          <Chip
            label={failed ? 'failed' : 'ok'}
            size="small"
            color={failed ? 'error' : 'success'}
          />
        );
      },
    },
    {
      field: 'brewed_at',
      headerName: 'Brewed',
      width: 160,
      valueFormatter: (value: string) => new Date(value).toLocaleDateString(),
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={items}
      total={total}
      loading={isLoading}
      paginationModel={paginationModel}
      onPaginationModelChange={onPaginationModelChange}
      sortModel={sortModel}
      onSortModelChange={onSortModelChange}
    />
  );
}
