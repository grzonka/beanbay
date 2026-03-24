import DataTable from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import { useBeans } from '@/features/beans/hooks';
import { fmtDate } from '@/utils/date';
import { usePaginationParams } from '@/utils/pagination';
import { Chip, MenuItem, TextField } from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useMemo, useState } from 'react';
import { type BagListItem, useAllBags } from './hooks';

const ALL_BEANS_PARAMS = {
  offset: 0,
  limit: 200,
  sort_by: 'name',
  sort_dir: 'asc' as const,
};

export default function BagsListPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setIncludeRetired,
  } = usePaginationParams('created_at');

  const [beanIdFilter, setBeanIdFilter] = useState<string>('');

  const { data: beansData } = useBeans(ALL_BEANS_PARAMS);

  const beansMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const bean of beansData?.items ?? []) {
      map[bean.id] = bean.name;
    }
    return map;
  }, [beansData]);

  const queryParams = useMemo(
    () => ({ ...params, ...(beanIdFilter ? { bean_id: beanIdFilter } : {}) }),
    [params, beanIdFilter],
  );

  const { data, isLoading } = useAllBags(queryParams);

  const columns: GridColDef<BagListItem>[] = useMemo(
    () => [
      {
        field: 'bean_id',
        headerName: 'Bean',
        flex: 1,
        minWidth: 150,
        renderCell: (p) => beansMap[p.row.bean_id] ?? p.row.bean_id,
        sortable: false,
      },
      {
        field: 'roast_date',
        headerName: 'Roast Date',
        width: 130,
        renderCell: (p) => fmtDate(p.row.roast_date),
      },
      {
        field: 'weight',
        headerName: 'Weight',
        width: 100,
        renderCell: (p) => (p.row.weight != null ? `${p.row.weight}g` : '—'),
      },
      {
        field: 'price',
        headerName: 'Price',
        width: 100,
        renderCell: (p) =>
          p.row.price != null ? `$${p.row.price.toFixed(2)}` : '—',
      },
      {
        field: 'is_preground',
        headerName: 'Pre-ground',
        width: 120,
        renderCell: (p) =>
          p.row.is_preground ? (
            <Chip label="Pre-ground" size="small" color="warning" />
          ) : null,
        sortable: false,
      },
      {
        field: 'opened_at',
        headerName: 'Opened',
        width: 130,
        renderCell: (p) => p.row.opened_at ?? '—',
      },
      {
        field: 'frozen_at',
        headerName: 'Frozen',
        width: 130,
        renderCell: (p) => p.row.frozen_at ?? '—',
      },
    ],
    [beansMap],
  );

  const beanOptions = beansData?.items ?? [];

  return (
    <>
      <PageHeader title="Bags" />
      <TextField
        select
        size="small"
        label="Filter by bean"
        value={beanIdFilter}
        onChange={(e) => setBeanIdFilter(e.target.value)}
        sx={{ mb: 2, minWidth: 220 }}
      >
        <MenuItem value="">All beans</MenuItem>
        {beanOptions.map((b) => (
          <MenuItem key={b.id} value={b.id}>
            {b.name}
          </MenuItem>
        ))}
      </TextField>
      <DataTable<BagListItem>
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
        emptyTitle="No bags found"
      />
    </>
  );
}
