import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

// ---- TypeScript interfaces ----

export interface Cupping {
  id: string;
  bag_id: string;
  person_id: string;
  cupped_at: string;
  dry_fragrance: number | null;
  wet_aroma: number | null;
  brightness: number | null;
  flavor: number | null;
  body: number | null;
  finish: number | null;
  sweetness: number | null;
  clean_cup: number | null;
  complexity: number | null;
  uniformity: number | null;
  cuppers_correction: number | null;
  total_score: number | null;
  notes: string | null;
  person_name: string;
  flavor_tags: { id: string; name: string }[];
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---- Cupping hooks ----

export function useCuppings(params: PaginationParams) {
  return useQuery<Paginated<Cupping>>({
    queryKey: ['cuppings', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/cuppings', { params });
      return data;
    },
  });
}

export function useCupping(id: string) {
  return useQuery<Cupping>({
    queryKey: ['cuppings', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/cuppings/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateCupping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.post('/cuppings', body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cuppings'] });
      qc.invalidateQueries({ queryKey: ['stats', 'cuppings'] });
    },
  });
}

export function useUpdateCupping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: { id: string; [key: string]: unknown }) => {
      const { data } = await apiClient.patch(`/cuppings/${id}`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cuppings'] });
      qc.invalidateQueries({ queryKey: ['stats', 'cuppings'] });
    },
  });
}

export function useDeleteCupping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/cuppings/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cuppings'] });
      qc.invalidateQueries({ queryKey: ['stats', 'cuppings'] });
    },
  });
}
