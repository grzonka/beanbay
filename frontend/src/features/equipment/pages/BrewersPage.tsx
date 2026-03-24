import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button, Chip, Stack } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';
import BrewerFormDialog from '../components/BrewerFormDialog';
import { type Brewer, brewerHooks } from '../hooks';

export default function BrewersPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('name');
  const { data, isLoading } = brewerHooks.useList(params);
  const deleteBrewer = brewerHooks.useDelete();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editBrewer, setEditBrewer] = useState<Brewer | null>(null);
  const [retireTarget, setRetireTarget] = useState<Brewer | null>(null);

  const updateBrewer = brewerHooks.useUpdate();

  const handleRetire = async () => {
    if (retireTarget) {
      await deleteBrewer.mutateAsync(retireTarget.id);
      notify('Brewer retired');
      setRetireTarget(null);
      setFormOpen(false);
    }
  };

  const handleActivate = async () => {
    if (editBrewer) {
      await updateBrewer.mutateAsync({ id: editBrewer.id, retired_at: null });
      notify('Brewer activated');
      setFormOpen(false);
      setEditBrewer(null);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 150 },
    {
      field: 'methods',
      headerName: 'Brew Methods',
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) => {
        const methods = (params.row as Brewer).methods;
        if (!methods?.length) return '—';
        return (
          <Stack
            direction="row"
            spacing={0.5}
            flexWrap="wrap"
            alignItems="center"
            height="100%"
          >
            {methods.map((m) => (
              <Chip key={m.id} label={m.name} size="small" variant="outlined" />
            ))}
          </Stack>
        );
      },
    },
    {
      field: 'tier',
      headerName: 'Tier',
      width: 80,
      renderCell: (params) => {
        const tier = params.value as number;
        if (tier == null) return '—';
        return <Chip label={`T${tier}`} size="small" color="primary" />;
      },
    },
  ];

  return (
    <>
      <PageHeader
        title="Brewers"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditBrewer(null);
              setFormOpen(true);
            }}
          >
            Add Brewer
          </Button>
        }
      />
      <DataTable<Brewer>
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
          setEditBrewer(row);
          setFormOpen(true);
        }}
        emptyTitle="No brewers yet"
        emptyActionLabel="Add Brewer"
        onEmptyAction={() => {
          setEditBrewer(null);
          setFormOpen(true);
        }}
      />
      <BrewerFormDialog
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditBrewer(null);
        }}
        brewer={editBrewer}
        onRetire={editBrewer ? () => setRetireTarget(editBrewer) : undefined}
        onActivate={editBrewer?.retired_at ? handleActivate : undefined}
      />
      <ConfirmDialog
        open={!!retireTarget}
        title="Retire Brewer"
        message={`Retire "${retireTarget?.name}"? This won't delete associated brews.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireTarget(null)}
      />
    </>
  );
}
