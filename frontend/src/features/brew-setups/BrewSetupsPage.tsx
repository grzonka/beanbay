import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';
import BrewSetupFormDialog from './BrewSetupFormDialog';
import {
  type BrewSetup,
  useBrewSetups,
  useDeleteBrewSetup,
  useUpdateBrewSetup,
} from './hooks';

export default function BrewSetupsPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('name');
  const { data, isLoading } = useBrewSetups(params);
  const deleteBrewSetup = useDeleteBrewSetup();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editSetup, setEditSetup] = useState<BrewSetup | null>(null);
  const [retireTarget, setRetireTarget] = useState<BrewSetup | null>(null);

  const updateBrewSetup = useUpdateBrewSetup();

  const handleRetire = async () => {
    if (retireTarget) {
      await deleteBrewSetup.mutateAsync(retireTarget.id);
      notify('Brew setup retired');
      setRetireTarget(null);
      setFormOpen(false);
    }
  };

  const handleActivate = async () => {
    if (editSetup) {
      await updateBrewSetup.mutateAsync({ id: editSetup.id, retired_at: null });
      notify('Brew setup activated');
      setFormOpen(false);
      setEditSetup(null);
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      renderCell: (params) => params.row.name || '—',
    },
    { field: 'brew_method_name', headerName: 'Brew Method', flex: 1 },
    {
      field: 'grinder_name',
      headerName: 'Grinder',
      flex: 1,
      renderCell: (params) => params.row.grinder_name || '—',
    },
    {
      field: 'brewer_name',
      headerName: 'Brewer',
      flex: 1,
      renderCell: (params) => params.row.brewer_name || '—',
    },
    {
      field: 'paper_name',
      headerName: 'Paper',
      width: 120,
      renderCell: (params) => params.row.paper_name || '—',
    },
    {
      field: 'water_name',
      headerName: 'Water',
      width: 120,
      renderCell: (params) => params.row.water_name || '—',
    },
  ];

  return (
    <>
      <PageHeader
        title="Brew Setups"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditSetup(null);
              setFormOpen(true);
            }}
          >
            Add Brew Setup
          </Button>
        }
      />
      <DataTable<BrewSetup>
        columns={columns}
        rows={data?.items ?? []}
        total={data?.total ?? 0}
        loading={isLoading}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        includeRetired={params.include_retired}
        onIncludeRetiredChange={setIncludeRetired}
        onRowClick={(row) => {
          setEditSetup(row);
          setFormOpen(true);
        }}
        emptyTitle="No brew setups yet"
        emptyActionLabel="Add Brew Setup"
        onEmptyAction={() => {
          setEditSetup(null);
          setFormOpen(true);
        }}
      />
      <BrewSetupFormDialog
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditSetup(null);
        }}
        brewSetup={editSetup}
        onRetire={editSetup ? () => setRetireTarget(editSetup) : undefined}
        onActivate={editSetup?.retired_at ? handleActivate : undefined}
      />
      <ConfirmDialog
        open={!!retireTarget}
        title="Retire Brew Setup"
        message={`Retire "${retireTarget?.name || retireTarget?.brew_method_name || 'this setup'}"? This won't delete any brews using it.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireTarget(null)}
      />
    </>
  );
}
