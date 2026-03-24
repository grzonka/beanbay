import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';
import PaperFormDialog from '../components/PaperFormDialog';
import { type Paper, paperHooks } from '../hooks';

export default function PapersPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('name');
  const { data, isLoading } = paperHooks.useList(params);
  const deletePaper = paperHooks.useDelete();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editPaper, setEditPaper] = useState<Paper | null>(null);
  const [retireTarget, setRetireTarget] = useState<Paper | null>(null);

  const updatePaper = paperHooks.useUpdate();

  const handleRetire = async () => {
    if (retireTarget) {
      await deletePaper.mutateAsync(retireTarget.id);
      notify('Paper retired');
      setRetireTarget(null);
      setFormOpen(false);
    }
  };

  const handleActivate = async () => {
    if (editPaper) {
      await updatePaper.mutateAsync({ id: editPaper.id, retired_at: null });
      notify('Paper activated');
      setFormOpen(false);
      setEditPaper(null);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 150 },
    { field: 'notes', headerName: 'Notes', flex: 1, minWidth: 150 },
  ];

  return (
    <>
      <PageHeader
        title="Papers"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditPaper(null);
              setFormOpen(true);
            }}
          >
            Add Paper
          </Button>
        }
      />
      <DataTable<Paper>
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
          setEditPaper(row);
          setFormOpen(true);
        }}
        emptyTitle="No papers yet"
        emptyActionLabel="Add Paper"
        onEmptyAction={() => {
          setEditPaper(null);
          setFormOpen(true);
        }}
      />
      <PaperFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        paper={editPaper}
        onRetire={editPaper ? () => setRetireTarget(editPaper) : undefined}
        onActivate={editPaper?.retired_at ? handleActivate : undefined}
      />
      <ConfirmDialog
        open={!!retireTarget}
        title="Retire Paper"
        message={`Retire "${retireTarget?.name}"?`}
        onConfirm={handleRetire}
        onCancel={() => setRetireTarget(null)}
      />
    </>
  );
}
