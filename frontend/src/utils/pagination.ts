import type { GridPaginationModel, GridSortModel } from '@mui/x-data-grid';
import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';

export interface PaginationParams {
  offset: number;
  limit: number;
  sort_by: string;
  sort_dir: 'asc' | 'desc';
  q?: string;
  include_retired?: boolean;
}

const DEFAULT_LIMIT = 25;

export function usePaginationParams(defaultSortBy = 'created_at') {
  const [searchParams, setSearchParams] = useSearchParams();

  const params: PaginationParams = useMemo(
    () => ({
      offset: Number.parseInt(searchParams.get('offset') ?? '0', 10),
      limit: Number.parseInt(
        searchParams.get('limit') ?? String(DEFAULT_LIMIT),
        10,
      ),
      sort_by: searchParams.get('sort_by') ?? defaultSortBy,
      sort_dir: (searchParams.get('sort_dir') as 'asc' | 'desc') ?? 'desc',
      q: searchParams.get('q') ?? undefined,
      include_retired: searchParams.get('include_retired') === 'true',
    }),
    [searchParams, defaultSortBy],
  );

  const paginationModel: GridPaginationModel = useMemo(
    () => ({
      page: Math.floor(params.offset / params.limit),
      pageSize: params.limit,
    }),
    [params.offset, params.limit],
  );

  const sortModel: GridSortModel = useMemo(() => {
    if (!params.sort_by) return [];
    return [{ field: params.sort_by, sort: params.sort_dir }];
  }, [params.sort_by, params.sort_dir]);

  const onPaginationModelChange = useCallback(
    (model: GridPaginationModel) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('offset', String(model.page * model.pageSize));
        next.set('limit', String(model.pageSize));
        return next;
      });
    },
    [setSearchParams],
  );

  const onSortModelChange = useCallback(
    (model: GridSortModel) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (model.length > 0) {
          next.set('sort_by', model[0].field);
          next.set('sort_dir', model[0].sort ?? 'asc');
        }
        next.set('offset', '0');
        return next;
      });
    },
    [setSearchParams],
  );

  const setSearch = useCallback(
    (q: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (q) next.set('q', q);
        else next.delete('q');
        next.set('offset', '0');
        return next;
      });
    },
    [setSearchParams],
  );

  const setIncludeRetired = useCallback(
    (include: boolean) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (include) next.set('include_retired', 'true');
        else next.delete('include_retired');
        next.set('offset', '0');
        return next;
      });
    },
    [setSearchParams],
  );

  return {
    params,
    paginationModel,
    sortModel,
    onPaginationModelChange,
    onSortModelChange,
    setSearch,
    setIncludeRetired,
  };
}

interface UsePaginationOptions {
  field: string;
  sort: 'asc' | 'desc';
}

/**
 * Local-state pagination hook for components that don't sync with URL params.
 *
 * Parameters
 * ----------
 * defaultSort : UsePaginationOptions
 *     Initial sort field and direction.
 *
 * Returns
 * -------
 * Object with paginationModel, onPaginationModelChange, sortModel, onSortModelChange.
 */
export function usePagination(defaultSort: UsePaginationOptions) {
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [sortModel, setSortModel] = useState<GridSortModel>([
    { field: defaultSort.field, sort: defaultSort.sort },
  ]);

  const onPaginationModelChange = useCallback((model: GridPaginationModel) => {
    setPaginationModel(model);
  }, []);

  const onSortModelChange = useCallback((model: GridSortModel) => {
    setSortModel(model);
  }, []);

  return {
    paginationModel,
    onPaginationModelChange,
    sortModel,
    onSortModelChange,
  };
}
