import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';
import GrinderFormDialog from '../components/GrinderFormDialog';
import { type Grinder, grinderHooks } from '../hooks';

export default function GrindersPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('name');
  const { data, isLoading } = grinderHooks.useList(params);
  const deleteGrinder = grinderHooks.useDelete();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editGrinder, setEditGrinder] = useState<Grinder | null>(null);
  const [retireTarget, setRetireTarget] = useState<Grinder | null>(null);

  const updateGrinder = grinderHooks.useUpdate();

  const handleRetire = async () => {
    if (retireTarget) {
      await deleteGrinder.mutateAsync(retireTarget.id);
      notify('Grinder retired');
      setRetireTarget(null);
      setFormOpen(false);
    }
  };

  const handleActivate = async () => {
    if (editGrinder) {
      await updateGrinder.mutateAsync({ id: editGrinder.id, retired_at: null });
      notify('Grinder activated');
      setFormOpen(false);
      setEditGrinder(null);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 150 },
    { field: 'dial_type', headerName: 'Dial Type', width: 120 },
    {
      field: 'grind_range',
      headerName: 'Grind Range',
      width: 150,
      renderCell: (params) => {
        const range = params.value as Grinder['grind_range'];
        if (!range) return '—';
        return `${range.min} - ${range.max}`;
      },
    },
  ];

  return (
    <>
      <PageHeader
        title="Grinders"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditGrinder(null);
              setFormOpen(true);
            }}
          >
            Add Grinder
          </Button>
        }
      />
      <DataTable<Grinder>
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
          setEditGrinder(row);
          setFormOpen(true);
        }}
        emptyTitle="No grinders yet"
        emptyActionLabel="Add Grinder"
        onEmptyAction={() => {
          setEditGrinder(null);
          setFormOpen(true);
        }}
      />
      <GrinderFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        grinder={editGrinder}
        onRetire={editGrinder ? () => setRetireTarget(editGrinder) : undefined}
        onActivate={editGrinder?.retired_at ? handleActivate : undefined}
      />
      <ConfirmDialog
        open={!!retireTarget}
        title="Retire Grinder"
        message={`Retire "${retireTarget?.name}"? This won't delete associated brews.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireTarget(null)}
      />
    </>
  );
}
