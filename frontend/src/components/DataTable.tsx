import EmptyState from '@/components/EmptyState';
import { Search as SearchIcon } from '@mui/icons-material';
import {
  Box,
  FormControlLabel,
  InputAdornment,
  Switch,
  TextField,
} from '@mui/material';
import {
  DataGrid,
  type GridColDef,
  type GridPaginationModel,
  type GridRowParams,
  type GridSortModel,
} from '@mui/x-data-grid';
import { debounce } from 'lodash-es';
// frontend/src/components/DataTable.tsx
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useNavigate } from 'react-router';

interface DataTableProps<T extends { id: string }> {
  columns: GridColDef[];
  rows: T[];
  total: number;
  loading: boolean;
  paginationModel: GridPaginationModel;
  onPaginationModelChange: (model: GridPaginationModel) => void;
  sortModel: GridSortModel;
  onSortModelChange: (model: GridSortModel) => void;
  search?: string;
  onSearchChange?: (q: string) => void;
  includeRetired?: boolean;
  onIncludeRetiredChange?: (include: boolean) => void;
  extraToolbarContent?: ReactNode;
  detailPath?: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
}

export default function DataTable<T extends { id: string }>({
  columns,
  rows,
  total,
  loading,
  paginationModel,
  onPaginationModelChange,
  sortModel,
  onSortModelChange,
  search,
  onSearchChange,
  includeRetired,
  onIncludeRetiredChange,
  extraToolbarContent,
  detailPath,
  onRowClick,
  emptyTitle = 'No items yet',
  emptyDescription,
  emptyActionLabel,
  onEmptyAction,
}: DataTableProps<T>) {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState(search ?? '');

  const debouncedSearch = useMemo(
    () => (onSearchChange ? debounce(onSearchChange, 300) : undefined),
    [onSearchChange],
  );
  useEffect(() => () => debouncedSearch?.cancel(), [debouncedSearch]);

  const handleRowClick = useCallback(
    (params: GridRowParams<T>) => {
      if (onRowClick) {
        onRowClick(params.row);
      } else if (detailPath) {
        navigate(detailPath(params.row));
      }
    },
    [navigate, detailPath, onRowClick],
  );

  if (!loading && rows.length === 0 && !search && !includeRetired) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
      />
    );
  }

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          mb: 2,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        {onSearchChange && (
          <TextField
            size="small"
            placeholder="Search..."
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              debouncedSearch?.(e.target.value);
            }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ maxWidth: 300 }}
          />
        )}
        {onIncludeRetiredChange && (
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={includeRetired ?? false}
                onChange={(_, checked) => onIncludeRetiredChange(checked)}
              />
            }
            label="Show retired"
          />
        )}
        {extraToolbarContent}
      </Box>
      <DataGrid
        rows={rows}
        columns={columns}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        pageSizeOptions={[10, 25, 50]}
        sortingMode="server"
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        onRowClick={handleRowClick}
        disableRowSelectionOnClick
        autoHeight
        sx={{
          border: 0,
          cursor: detailPath || onRowClick ? 'pointer' : 'default',
          '& .MuiDataGrid-row:hover':
            detailPath || onRowClick ? { bgcolor: 'action.hover' } : {},
        }}
      />
    </Box>
  );
}
