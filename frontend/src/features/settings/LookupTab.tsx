import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import { usePaginationParams } from '@/utils/pagination';
import {
  Add as AddIcon,
  Archive as ArchiveIcon,
  RestoreFromTrash as RestoreFromTrashIcon,
} from '@mui/icons-material';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useEffect, useState } from 'react';
import type { LookupItem } from './hooks';

interface FieldConfig {
  name: string;
  label: string;
  required?: boolean;
}

interface LookupTabProps {
  hooks: ReturnType<typeof import('./hooks').createLookupHooks>;
  columns: GridColDef[];
  fields: FieldConfig[];
  entityName: string;
}

export default function LookupTab({
  hooks,
  columns,
  fields,
  entityName,
}: LookupTabProps) {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('name');
  const { data, isLoading } = hooks.useList(params);
  const create = hooks.useCreate();
  const update = hooks.useUpdate();
  const del = hooks.useDelete();
  const { notify } = useNotification();

  const [formOpen, setFormOpen] = useState(false);
  const [editItem, setEditItem] = useState<LookupItem | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [deleteTarget, setDeleteTarget] = useState<LookupItem | null>(null);

  useEffect(() => {
    if (editItem) {
      const values: Record<string, string> = {};
      fields.forEach((f) => {
        values[f.name] = String(editItem[f.name] ?? '');
      });
      setFormValues(values);
    } else {
      const values: Record<string, string> = {};
      fields.forEach((f) => {
        values[f.name] = '';
      });
      setFormValues(values);
    }
  }, [editItem, formOpen, fields]);

  const handleSubmit = async () => {
    const body: Record<string, unknown> = {};
    fields.forEach((f) => {
      body[f.name] = formValues[f.name] || null;
    });
    if (editItem) {
      await update.mutateAsync({ id: editItem.id, ...body });
      notify(`${entityName} updated`);
    } else {
      await create.mutateAsync(body);
      notify(`${entityName} created`);
    }
    setFormOpen(false);
    setEditItem(null);
  };

  const handleDelete = async () => {
    if (deleteTarget) {
      await del.mutateAsync(deleteTarget.id);
      notify(`${entityName} retired`);
      setDeleteTarget(null);
      setFormOpen(false);
    }
  };

  const handleActivate = async () => {
    if (editItem) {
      await update.mutateAsync({ id: editItem.id, retired_at: null });
      notify(`${entityName} activated`);
      setFormOpen(false);
      setEditItem(null);
    }
  };

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<AddIcon />}
        onClick={() => {
          setEditItem(null);
          setFormOpen(true);
        }}
        sx={{ mb: 2 }}
      >
        Add {entityName}
      </Button>
      <DataTable<LookupItem>
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
          setEditItem(row);
          setFormOpen(true);
        }}
        emptyTitle={`No ${entityName.toLowerCase()}s yet`}
        emptyActionLabel={`Add ${entityName}`}
        onEmptyAction={() => {
          setEditItem(null);
          setFormOpen(true);
        }}
      />
      <Dialog
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditItem(null);
        }}
      >
        <DialogTitle>
          {editItem ? `Edit ${entityName}` : `Add ${entityName}`}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {fields.map((f) => (
              <TextField
                key={f.name}
                label={f.label}
                value={formValues[f.name] ?? ''}
                onChange={(e) =>
                  setFormValues((prev) => ({
                    ...prev,
                    [f.name]: e.target.value,
                  }))
                }
                required={f.required}
              />
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          {editItem?.retired_at && (
            <Button
              color="success"
              onClick={handleActivate}
              sx={{ mr: 'auto' }}
              startIcon={<RestoreFromTrashIcon />}
            >
              Activate
            </Button>
          )}
          {editItem && !editItem.retired_at && (
            <Button
              color="warning"
              onClick={() => setDeleteTarget(editItem)}
              sx={{ mr: 'auto' }}
              startIcon={<ArchiveIcon />}
            >
              Retire
            </Button>
          )}
          <Button
            onClick={() => {
              setFormOpen(false);
              setEditItem(null);
            }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={fields.some(
              (f) => f.required && !formValues[f.name]?.trim(),
            )}
          >
            {editItem ? 'Save' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Retire ${entityName}`}
        message={`Retire "${deleteTarget?.name}"?`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
