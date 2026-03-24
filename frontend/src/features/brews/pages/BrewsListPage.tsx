import DataTable from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import { fmtDate } from '@/utils/date';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button, Chip } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useMemo } from 'react';
import { useNavigate } from 'react-router';
import { type BrewListItem, useBrews } from '../hooks';

export default function BrewsListPage() {
  const navigate = useNavigate();

  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setSearch,
    setIncludeRetired,
  } = usePaginationParams('brewed_at');

  const { data, isLoading } = useBrews(params);

  const columns: GridColDef<BrewListItem>[] = useMemo(
    () => [
      { field: 'bean_name', headerName: 'Bean', flex: 1, minWidth: 150 },
      { field: 'brew_method_name', headerName: 'Method', width: 120 },
      { field: 'person_name', headerName: 'Person', width: 120 },
      { field: 'dose', headerName: 'Dose (g)', width: 90 },
      {
        field: 'yield_amount',
        headerName: 'Yield (g)',
        width: 90,
        renderCell: (p) => p.row.yield_amount ?? '—',
      },
      {
        field: 'grind_setting_display',
        headerName: 'Grind',
        width: 90,
        renderCell: (p) => p.row.grind_setting_display || '—',
      },
      {
        field: 'temperature',
        headerName: 'Temp (°C)',
        width: 90,
        renderCell: (p) => p.row.temperature ?? '—',
      },
      {
        field: 'score',
        headerName: 'Score',
        width: 80,
        renderCell: (p) => p.row.score?.toFixed(1) ?? '—',
      },
      {
        field: 'brewed_at',
        headerName: 'Brewed',
        width: 150,
        renderCell: (p) => fmtDate(p.row.brewed_at),
      },
      {
        field: 'is_failed',
        headerName: '',
        width: 70,
        sortable: false,
        renderCell: (p) =>
          p.row.is_failed ? (
            <Chip label="FAIL" size="small" color="error" />
          ) : null,
      },
    ],
    [],
  );

  return (
    <>
      <PageHeader
        title="Brews"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/brews/new')}
          >
            Log a Brew
          </Button>
        }
      />
      <DataTable<BrewListItem>
        columns={columns}
        rows={data?.items ?? []}
        total={data?.total ?? 0}
        loading={isLoading}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        search={params.q}
        onSearchChange={setSearch}
        includeRetired={params.include_retired}
        onIncludeRetiredChange={setIncludeRetired}
        detailPath={(row) => `/brews/${row.id}`}
        emptyTitle="No brews yet"
      />
    </>
  );
}
