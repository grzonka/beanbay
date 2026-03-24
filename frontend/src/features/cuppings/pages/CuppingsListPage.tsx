import apiClient from '@/api/client';
import DataTable from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import { fmtDateTime } from '@/utils/date';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import { Button } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import CuppingFormDialog from '../components/CuppingFormDialog';
import { type Cupping, useCuppings } from '../hooks';

export default function CuppingsListPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('cupped_at');

  const { data, isLoading } = useCuppings(params);
  const [formOpen, setFormOpen] = useState(false);

  const { data: bagsData } = useQuery({
    queryKey: ['bags', 'all'],
    queryFn: async () => {
      const { data } = await apiClient.get('/bags', { params: { limit: 200 } });
      return data;
    },
  });
  const { data: beansData } = useQuery({
    queryKey: ['beans', 'all'],
    queryFn: async () => {
      const { data } = await apiClient.get('/beans', {
        params: { limit: 200 },
      });
      return data;
    },
  });

  const beanMap = new Map<string, string>();
  beansData?.items?.forEach((b: any) => beanMap.set(b.id, b.name));
  const bagToBeanName = new Map<string, string>();
  bagsData?.items?.forEach((bag: any) => {
    bagToBeanName.set(bag.id, beanMap.get(bag.bean_id) ?? 'Unknown');
  });

  const columns: GridColDef<Cupping>[] = [
    {
      field: 'bag_id',
      headerName: 'Bean',
      flex: 1,
      minWidth: 140,
      renderCell: (p) => bagToBeanName.get(p.value as string) ?? '—',
    },
    { field: 'person_name', headerName: 'Person', flex: 1, minWidth: 140 },
    {
      field: 'total_score',
      headerName: 'Total Score',
      width: 130,
      renderCell: (p) => (p.value != null ? p.value.toFixed(2) : '—'),
    },
    {
      field: 'cupped_at',
      headerName: 'Cupped At',
      width: 180,
      renderCell: (p) => fmtDateTime(p.value as string),
    },
  ];

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
        includeRetired={params.include_retired}
        onIncludeRetiredChange={setIncludeRetired}
        detailPath={(row) => `/cuppings/${row.id}`}
        emptyTitle="No cuppings yet"
        emptyActionLabel="Add Cupping"
        onEmptyAction={() => setFormOpen(true)}
      />
      <CuppingFormDialog open={formOpen} onClose={() => setFormOpen(false)} />
    </>
  );
}
