import DataTable from '@/components/DataTable';
import PageHeader from '@/components/PageHeader';
import RatingFormDialog from '@/features/ratings/RatingFormDialog';
import { usePaginationParams } from '@/utils/pagination';
import { Add as AddIcon } from '@mui/icons-material';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Switch,
  Typography,
} from '@mui/material';
import type { GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';
import BagFormDialog from '../components/BagFormDialog';
import BeanFormDialog from '../components/BeanFormDialog';
import { type Bean, useBeans } from '../hooks';

const columns: GridColDef<Bean>[] = [
  { field: 'name', headerName: 'Name', flex: 1, minWidth: 150 },
  {
    field: 'roaster',
    headerName: 'Roaster',
    width: 160,
    renderCell: (params) => params.row.roaster?.name ?? '—',
    sortable: false,
  },
  { field: 'bean_mix_type', headerName: 'Mix Type', width: 130 },
  { field: 'bean_use_type', headerName: 'Use Type', width: 120 },
  { field: 'roast_degree', headerName: 'Roast Degree', width: 130 },
  {
    field: 'bags',
    headerName: 'Bags',
    width: 80,
    renderCell: (params) => params.row.bags?.length ?? 0,
    sortable: false,
  },
];

export default function BeansListPage() {
  const {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setSearch,
    setIncludeRetired,
  } = usePaginationParams('name');

  const { data, isLoading } = useBeans(params);
  const [formOpen, setFormOpen] = useState(false);
  const [editBean, setEditBean] = useState<Bean | null>(null);

  // Active bags filter
  const [hasActiveBags, setHasActiveBags] = useState(false);

  // New bean creation flow
  const [newBeanId, setNewBeanId] = useState<string | null>(null);
  const [bagFormOpen, setBagFormOpen] = useState(false);
  const [ratingPromptOpen, setRatingPromptOpen] = useState(false);
  const [ratingFormOpen, setRatingFormOpen] = useState(false);

  const handleBeanCreated = (bean: Bean) => {
    setNewBeanId(bean.id);
    setBagFormOpen(true);
  };

  const handleBagClose = () => {
    setBagFormOpen(false);
    setRatingPromptOpen(true);
  };

  const handleRatingPromptYes = () => {
    setRatingPromptOpen(false);
    setRatingFormOpen(true);
  };

  const handleRatingPromptNo = () => {
    setRatingPromptOpen(false);
    setNewBeanId(null);
  };

  const handleRatingFormClose = () => {
    setRatingFormOpen(false);
    setNewBeanId(null);
  };

  const displayedRows = hasActiveBags
    ? (data?.items ?? []).filter((bean) => (bean.bags?.length ?? 0) > 0)
    : (data?.items ?? []);

  return (
    <>
      <PageHeader
        title="Beans"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditBean(null);
              setFormOpen(true);
            }}
          >
            Add Bean
          </Button>
        }
      />
      <DataTable<Bean>
        columns={columns}
        rows={displayedRows}
        total={hasActiveBags ? displayedRows.length : (data?.total ?? 0)}
        loading={isLoading}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        search={params.q}
        onSearchChange={setSearch}
        includeRetired={params.include_retired}
        onIncludeRetiredChange={setIncludeRetired}
        extraToolbarContent={
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={hasActiveBags}
                onChange={(_, c) => setHasActiveBags(c)}
              />
            }
            label="Has active bags"
            sx={{ ml: 1 }}
          />
        }
        detailPath={(row) => `/beans/${row.id}`}
        emptyTitle="No beans yet"
        emptyActionLabel="Add Bean"
        onEmptyAction={() => {
          setEditBean(null);
          setFormOpen(true);
        }}
      />
      <BeanFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        bean={editBean}
        onCreated={handleBeanCreated}
      />
      {newBeanId && (
        <BagFormDialog
          open={bagFormOpen}
          onClose={handleBagClose}
          beanId={newBeanId}
        />
      )}
      <Dialog open={ratingPromptOpen} onClose={handleRatingPromptNo}>
        <DialogTitle>Add a taste rating?</DialogTitle>
        <DialogContent>
          <Typography>
            Would you like to add a taste rating for this bean?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleRatingPromptNo}>No</Button>
          <Button variant="contained" onClick={handleRatingPromptYes}>
            Yes
          </Button>
        </DialogActions>
      </Dialog>
      {newBeanId && (
        <RatingFormDialog
          open={ratingFormOpen}
          onClose={handleRatingFormClose}
          beanId={newBeanId}
        />
      )}
    </>
  );
}
