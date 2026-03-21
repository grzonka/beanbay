import { useMemo } from 'react';
import { type GridColDef } from '@mui/x-data-grid';
import { Button, Chip } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router';
import PageHeader from '@/components/PageHeader';
import DataTable from '@/components/DataTable';
import { usePaginationParams } from '@/utils/pagination';
import { useBrews, type BrewListItem } from '../hooks';

export default function BrewsListPage() {
  const navigate = useNavigate();

  const {
    params, paginationModel, sortModel,
    onPaginationModelChange, onSortModelChange,
    setSearch, setIncludeRetired,
  } = usePaginationParams('brewed_at');

  const { data, isLoading } = useBrews(params);

  const columns: GridColDef<BrewListItem>[] = useMemo(
    () => [
      { field: 'bean_name', headerName: 'Bean', flex: 1, minWidth: 150 },
      { field: 'brew_method_name', headerName: 'Method', width: 120 },
      { field: 'person_name', headerName: 'Person', width: 120 },
      { field: 'dose', headerName: 'Dose (g)', width: 90 },
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
        renderCell: (p) => new Date(p.row.brewed_at).toLocaleDateString(),
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
