import { useState } from 'react';
import { type GridColDef } from '@mui/x-data-grid';
import { Button } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import PageHeader from '@/components/PageHeader';
import DataTable from '@/components/DataTable';
import { usePaginationParams } from '@/utils/pagination';
import { useCuppings, type Cupping } from '../hooks';
import CuppingFormDialog from '../components/CuppingFormDialog';

const columns: GridColDef<Cupping>[] = [
  { field: 'person_name', headerName: 'Person', flex: 1, minWidth: 140 },
  {
    field: 'total_score',
    headerName: 'Total Score',
    width: 130,
    renderCell: (p) => p.value != null ? p.value.toFixed(2) : '—',
  },
  {
    field: 'cupped_at',
    headerName: 'Cupped At',
    width: 180,
    renderCell: (p) => p.value ? new Date(p.value as string).toLocaleString() : '—',
  },
];

export default function CuppingsListPage() {
  const {
    params, paginationModel, sortModel,
    onPaginationModelChange, onSortModelChange,
    setSearch, setIncludeRetired,
  } = usePaginationParams('cupped_at');

  const { data, isLoading } = useCuppings(params);
  const [formOpen, setFormOpen] = useState(false);

  return (
    <>
      <PageHeader
        title="Cuppings"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setFormOpen(true)}
          >
            Add Cupping
          </Button>
        }
      />
      <DataTable<Cupping>
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
        detailPath={(row) => `/cuppings/${row.id}`}
        emptyTitle="No cuppings yet"
        emptyActionLabel="Add Cupping"
        onEmptyAction={() => setFormOpen(true)}
      />
      <CuppingFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
      />
    </>
  );
}
