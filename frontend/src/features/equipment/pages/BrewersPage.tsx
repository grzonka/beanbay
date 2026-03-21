import { useState } from 'react';
import { type GridColDef } from '@mui/x-data-grid';
import { Button, Chip, IconButton, Stack } from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Archive as ArchiveIcon } from '@mui/icons-material';
import PageHeader from '@/components/PageHeader';
import DataTable from '@/components/DataTable';
import ConfirmDialog from '@/components/ConfirmDialog';
import { usePaginationParams } from '@/utils/pagination';
import { brewerHooks, type Brewer } from '../hooks';
import BrewerFormDialog from '../components/BrewerFormDialog';
import { useNotification } from '@/components/NotificationProvider';

export default function BrewersPage() {
  const { params, paginationModel, sortModel, onPaginationModelChange, onSortModelChange, setSearch, setIncludeRetired } =
    usePaginationParams('name');
  const { data, isLoading } = brewerHooks.useList(params);
  const deleteBrewer = brewerHooks.useDelete();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editBrewer, setEditBrewer] = useState<Brewer | null>(null);
  const [retireTarget, setRetireTarget] = useState<Brewer | null>(null);

  const handleRetire = async () => {
    if (retireTarget) {
      await deleteBrewer.mutateAsync(retireTarget.id);
      notify('Brewer retired');
      setRetireTarget(null);
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
          <Stack direction="row" spacing={0.5} flexWrap="wrap" alignItems="center" height="100%">
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
    {
      field: 'actions',
      headerName: '',
      width: 88,
      sortable: false,
      renderCell: (params) => (
        <Stack direction="row" spacing={0.5} alignItems="center" height="100%">
          <IconButton
            size="small"
            aria-label="Edit brewer"
            onClick={(e) => {
              e.stopPropagation();
              setEditBrewer(params.row as Brewer);
              setFormOpen(true);
            }}
          >
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            aria-label="Retire brewer"
            onClick={(e) => {
              e.stopPropagation();
              setRetireTarget(params.row as Brewer);
            }}
          >
            <ArchiveIcon fontSize="small" />
          </IconButton>
        </Stack>
      ),
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
            onClick={() => { setEditBrewer(null); setFormOpen(true); }}
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
        search={params.q}
        onSearchChange={setSearch}
        includeRetired={params.include_retired}
        onIncludeRetiredChange={setIncludeRetired}
        emptyTitle="No brewers yet"
        emptyActionLabel="Add Brewer"
        onEmptyAction={() => { setEditBrewer(null); setFormOpen(true); }}
      />
      <BrewerFormDialog
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditBrewer(null); }}
        brewer={editBrewer}
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
