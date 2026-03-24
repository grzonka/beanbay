import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface LookupItem {
  id: string;
  name: string;
  created_at: string;
  retired_at: string | null;
  is_retired: boolean;
  [key: string]: unknown;
}

export function createLookupHooks(endpoint: string) {
  const queryKey = [endpoint];
  return {
    useList: (params: PaginationParams) =>
      useQuery({
        queryKey: [...queryKey, params],
        queryFn: async () => {
          const { data } = await apiClient.get(`/${endpoint}`, { params });
          return data as { items: LookupItem[]; total: number };
        },
      }),
    useCreate: () => {
      const qc = useQueryClient();
      return useMutation({
        mutationFn: async (body: Record<string, unknown>) => {
          const { data } = await apiClient.post(`/${endpoint}`, body);
          return data;
        },
        onSuccess: () => qc.invalidateQueries({ queryKey }),
      });
    },
    useUpdate: () => {
      const qc = useQueryClient();
      return useMutation({
        mutationFn: async ({
          id,
          ...body
        }: { id: string; [key: string]: unknown }) => {
          const { data } = await apiClient.patch(`/${endpoint}/${id}`, body);
          return data;
        },
        onSuccess: () => qc.invalidateQueries({ queryKey }),
      });
    },
    useDelete: () => {
      const qc = useQueryClient();
      return useMutation({
        mutationFn: async (id: string) => {
          await apiClient.delete(`/${endpoint}/${id}`);
        },
        onSuccess: () => qc.invalidateQueries({ queryKey }),
      });
    },
  };
}

export const flavorTagHooks = createLookupHooks('flavor-tags');
export const originHooks = createLookupHooks('origins');
export const roasterHooks = createLookupHooks('roasters');
export const processMethodHooks = createLookupHooks('process-methods');
export const beanVarietyHooks = createLookupHooks('bean-varieties');
export const brewMethodHooks = createLookupHooks('brew-methods');
export const stopModeHooks = createLookupHooks('stop-modes');
export const vendorHooks = createLookupHooks('vendors');
export const storageTypeHooks = createLookupHooks('storage-types');
