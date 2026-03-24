import apiClient from '@/api/client';
import ConfirmDialog from '@/components/ConfirmDialog';
import DataTable from '@/components/DataTable';
import { useNotification } from '@/components/NotificationProvider';
import PageHeader from '@/components/PageHeader';
import RatingFormDialog from '@/features/ratings/RatingFormDialog';
import { fmtDate } from '@/utils/date';
import { usePaginationParams } from '@/utils/pagination';
import {
  Add as AddIcon,
  Archive as ArchiveIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useParams } from 'react-router';
import BagFormDialog from '../components/BagFormDialog';
import BeanFormDialog from '../components/BeanFormDialog';
import {
  type Bag,
  type Bean,
  type BeanRating,
  useBags,
  useBean,
  useBeanRatings,
  useDeleteBag,
  useDeleteBean,
  useUpdateBag,
} from '../hooks';

// Base columns for Bags sub-table (actions column added inside BagsSection)
const baseBagColumns: GridColDef<Bag>[] = [
  {
    field: 'roast_date',
    headerName: 'Roast Date',
    width: 130,
    renderCell: (p) => fmtDate(p.value as string),
  },
  {
    field: 'weight',
    headerName: 'Weight (g)',
    width: 120,
    renderCell: (p) => (p.value != null ? `${p.value} g` : '—'),
  },
  {
    field: 'price',
    headerName: 'Price',
    width: 100,
    renderCell: (p) => (p.value != null ? `${p.value}` : '—'),
  },
  {
    field: 'is_preground',
    headerName: 'Pre-ground',
    width: 120,
    renderCell: (p) =>
      p.value ? <Chip label="Yes" size="small" color="warning" /> : null,
  },
  {
    field: 'opened_at',
    headerName: 'Opened At',
    width: 130,
    renderCell: (p) => p.value ?? '—',
  },
];

// Columns for Ratings sub-table
const ratingColumns: GridColDef<BeanRating>[] = [
  {
    field: 'person_name',
    headerName: 'Person',
    flex: 1,
    renderCell: (p) => p.value ?? '—',
  },
  {
    field: 'rated_at',
    headerName: 'Rated At',
    width: 130,
    renderCell: (p) => fmtDate(p.value as string),
  },
  {
    field: 'taste',
    headerName: 'Score',
    width: 100,
    renderCell: (p) => (p.row.taste?.score != null ? p.row.taste.score : '—'),
    sortable: false,
  },
];

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={2} alignItems="flex-start">
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
        {label}
      </Typography>
      <Typography variant="body2">{value ?? '—'}</Typography>
    </Stack>
  );
}

function BeanInfoCard({ bean }: { bean: Bean }) {
  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Stack spacing={1.5}>
          <InfoRow label="Roaster" value={bean.roaster?.name} />
          <InfoRow label="Mix Type" value={bean.bean_mix_type} />
          <InfoRow label="Use Type" value={bean.bean_use_type} />
          <InfoRow label="Roast Degree" value={bean.roast_degree} />
          <InfoRow label="Decaf" value={bean.decaf ? 'Yes' : 'No'} />
          {bean.url && (
            <InfoRow
              label="URL"
              value={
                <a href={bean.url} target="_blank" rel="noreferrer">
                  {bean.url}
                </a>
              }
            />
          )}
          {bean.ean && <InfoRow label="EAN" value={bean.ean} />}
          {bean.notes && <InfoRow label="Notes" value={bean.notes} />}

          {bean.origins.length > 0 && (
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              flexWrap="wrap"
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ minWidth: 140 }}
              >
                Origins
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap">
                {bean.origins.map((o) => (
                  <Chip
                    key={o.origin_id}
                    label={
                      o.percentage != null
                        ? `${o.origin_name} (${o.percentage}%)`
                        : o.origin_name
                    }
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Stack>
          )}

          {bean.processes.length > 0 && (
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              flexWrap="wrap"
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ minWidth: 140 }}
              >
                Processes
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap">
                {bean.processes.map((p) => (
                  <Chip
                    key={p.id}
                    label={p.name}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Stack>
          )}

          {bean.varieties.length > 0 && (
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              flexWrap="wrap"
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ minWidth: 140 }}
              >
                Varieties
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap">
                {bean.varieties.map((v) => (
                  <Chip
                    key={v.id}
                    label={v.name}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Stack>
          )}

          {bean.flavor_tags.length > 0 && (
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              flexWrap="wrap"
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ minWidth: 140 }}
              >
                Flavor Tags
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap">
                {bean.flavor_tags.map((t) => (
                  <Chip
                    key={t.id}
                    label={t.name}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Stack>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function BagsSection({ beanId }: { beanId: string }) {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
  } = usePaginationParams('roast_date');
  const { data, isLoading } = useBags(beanId, params);
  const deleteBag = useDeleteBag(beanId);
  const updateBag = useUpdateBag(beanId);
  const { notify } = useNotification();

  const [bagFormOpen, setBagFormOpen] = useState(false);
  const [editBag, setEditBag] = useState<Bag | null>(null);
  const [retireBagTarget, setRetireBagTarget] = useState<Bag | null>(null);

  const handleRetireBag = async () => {
    if (retireBagTarget) {
      await deleteBag.mutateAsync(retireBagTarget.id);
      notify('Bag retired');
      setRetireBagTarget(null);
      setBagFormOpen(false);
    }
  };

  const handleActivateBag = async () => {
    if (editBag) {
      await updateBag.mutateAsync({ id: editBag.id, retired_at: null });
      notify('Bag activated');
      setBagFormOpen(false);
      setEditBag(null);
    }
  };

  return (
    <Box sx={{ mb: 4 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h6">Bags</Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<AddIcon />}
          onClick={() => {
            setEditBag(null);
            setBagFormOpen(true);
          }}
        >
          Add Bag
        </Button>
      </Stack>
      <DataTable<Bag>
        columns={baseBagColumns}
        rows={data?.items ?? []}
        total={data?.total ?? 0}
        loading={isLoading}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        onRowClick={(row) => {
          setEditBag(row);
          setBagFormOpen(true);
        }}
        emptyTitle="No bags yet"
        emptyActionLabel="Add Bag"
        onEmptyAction={() => {
          setEditBag(null);
          setBagFormOpen(true);
        }}
      />
      <BagFormDialog
        open={bagFormOpen}
        onClose={() => setBagFormOpen(false)}
        beanId={beanId}
        bag={editBag}
        onRetire={
          editBag && !editBag.retired_at
            ? () => setRetireBagTarget(editBag)
            : undefined
        }
        onActivate={editBag?.retired_at ? handleActivateBag : undefined}
      />
      <ConfirmDialog
        open={!!retireBagTarget}
        title="Retire Bag"
        message="Retire this bag? It will be hidden but not deleted."
        onConfirm={handleRetireBag}
        onCancel={() => setRetireBagTarget(null)}
      />
    </Box>
  );
}

function RatingsSection({ beanId }: { beanId: string }) {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
  } = usePaginationParams('rated_at');
  const { data, isLoading } = useBeanRatings(beanId, params);

  const [ratingFormOpen, setRatingFormOpen] = useState(false);

  return (
    <Box>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h6">Ratings</Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setRatingFormOpen(true)}
        >
          Add Rating
        </Button>
      </Stack>
      <DataTable<BeanRating>
        columns={ratingColumns}
        rows={data?.items ?? []}
        total={data?.total ?? 0}
        loading={isLoading}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        detailPath={(row) => `/bean-ratings/${row.id}`}
        emptyTitle="No ratings yet"
        emptyActionLabel="Add Rating"
        onEmptyAction={() => setRatingFormOpen(true)}
      />
      <RatingFormDialog
        open={ratingFormOpen}
        onClose={() => setRatingFormOpen(false)}
        beanId={beanId}
      />
    </Box>
  );
}

interface CuppingSummary {
  id: string;
  person_name: string;
  total_score: number | null;
  cupped_at: string;
}

const cuppingColumns: GridColDef<CuppingSummary>[] = [
  { field: 'person_name', headerName: 'Person', flex: 1 },
  {
    field: 'total_score',
    headerName: 'Score',
    width: 100,
    renderCell: (p) => (p.value != null ? (p.value as number).toFixed(1) : '—'),
  },
  {
    field: 'cupped_at',
    headerName: 'Cupped At',
    width: 130,
    renderCell: (p) => fmtDate(p.value as string),
  },
];

function CuppingsSection({ beanId, bags }: { beanId: string; bags: Bag[] }) {
  const bagIds = bags.map((b) => b.id);

  const { data, isLoading } = useQuery<CuppingSummary[]>({
    queryKey: ['beans', beanId, 'cuppings'],
    queryFn: async () => {
      if (bagIds.length === 0) return [];
      // Fetch cuppings for each bag in parallel
      const results = await Promise.all(
        bagIds.map((bagId) =>
          apiClient
            .get('/cuppings', { params: { bag_id: bagId, limit: 100 } })
            .then((r) => r.data.items),
        ),
      );
      return results.flat();
    },
    enabled: bagIds.length > 0,
  });

  const cuppings = data ?? [];

  return (
    <Box>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h6">Cuppings</Typography>
      </Stack>
      <DataTable<CuppingSummary>
        columns={cuppingColumns}
        rows={cuppings}
        total={cuppings.length}
        loading={isLoading}
        paginationModel={{ page: 0, pageSize: 25 }}
        onPaginationModelChange={() => {}}
        sortModel={[]}
        onSortModelChange={() => {}}
        detailPath={(row) => `/cuppings/${row.id}`}
        emptyTitle="No cuppings yet"
      />
    </Box>
  );
}

export default function BeanDetailPage() {
  const { beanId } = useParams<{ beanId: string }>();
  const deleteBean = useDeleteBean();
  const { notify } = useNotification();

  const { data: bean, isLoading } = useBean(beanId ?? '');

  const [formOpen, setFormOpen] = useState(false);
  const [retireOpen, setRetireOpen] = useState(false);

  const handleRetire = async () => {
    if (bean) {
      await deleteBean.mutateAsync(bean.id);
      notify('Bean retired');
      setRetireOpen(false);
    }
  };

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="40vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!bean) {
    return <Typography>Bean not found.</Typography>;
  }

  return (
    <>
      <PageHeader
        title={bean.name}
        breadcrumbs={[{ label: 'Beans', to: '/beans' }, { label: bean.name }]}
        actions={
          <>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => setFormOpen(true)}
            >
              Edit
            </Button>
            <Button
              variant="outlined"
              color="warning"
              startIcon={<ArchiveIcon />}
              onClick={() => setRetireOpen(true)}
            >
              Retire
            </Button>
          </>
        }
      />

      <BeanInfoCard bean={bean} />

      <Divider sx={{ mb: 3 }} />

      <BagsSection beanId={bean.id} />

      <Divider sx={{ mb: 3 }} />

      <RatingsSection beanId={bean.id} />

      <Divider sx={{ mb: 3 }} />

      <CuppingsSection beanId={bean.id} bags={bean.bags ?? []} />

      <BeanFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        bean={bean}
      />

      <ConfirmDialog
        open={retireOpen}
        title="Retire Bean"
        message={`Retire "${bean.name}"? It will be hidden but not deleted.`}
        onConfirm={handleRetire}
        onCancel={() => setRetireOpen(false)}
      />
    </>
  );
}
