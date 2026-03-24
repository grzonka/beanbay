import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';
import WaterFormDialog from '../components/WaterFormDialog';
import { type Water, waterHooks } from '../hooks';

export default function WatersPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('name');
  const { data, isLoading } = waterHooks.useList(params);
  const deleteWater = waterHooks.useDelete();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editWater, setEditWater] = useState<Water | null>(null);
  const [retireTarget, setRetireTarget] = useState<Water | null>(null);

  const updateWater = waterHooks.useUpdate();

  const handleRetire = async () => {
    if (retireTarget) {
      await deleteWater.mutateAsync(retireTarget.id);
      notify('Water retired');
      setRetireTarget(null);
      setFormOpen(false);
    }
  };

  const handleActivate = async () => {
    if (editWater) {
      await updateWater.mutateAsync({ id: editWater.id, retired_at: null });
      notify('Water activated');
      setFormOpen(false);
      setEditWater(null);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 150 },
    {
      field: 'minerals',
      headerName: 'Minerals',
      flex: 1,
      minWidth: 100,
      renderCell: (params) => params.row.minerals.length,
    },
  ];

  return (
    <>
      <PageHeader
        title="Waters"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditWater(null);
              setFormOpen(true);
            }}
          >
            Add Water
          </Button>
        }
      />
      <DataTable<Water>
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
          setEditWater(row);
          setFormOpen(true);
        }}
        emptyTitle="No waters yet"
        emptyActionLabel="Add Water"
        onEmptyAction={() => {
          setEditWater(null);
          setFormOpen(true);
        }}
      />
      <WaterFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        water={editWater}
        onRetire={editWater ? () => setRetireTarget(editWater) : undefined}
        onActivate={editWater?.retired_at ? handleActivate : undefined}
      />
      <ConfirmDialog
        open={!!retireTarget}
        title="Retire Water"
        message={`Retire "${retireTarget?.name}"?`}
        onConfirm={handleRetire}
        onCancel={() => setRetireTarget(null)}
      />
    </>
  );
}
