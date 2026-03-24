import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface Person {
  id: string;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

interface PaginatedPeople {
  items: Person[];
  total: number;
  limit: number;
  offset: number;
}

export function usePeople(params: PaginationParams) {
  return useQuery<PaginatedPeople>({
    queryKey: ['people', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/people', { params });
      return data;
    },
  });
}

export function useCreatePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string }) => {
      const { data } = await apiClient.post('/people', body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['people'] }),
  });
}

export function useUpdatePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: {
      id: string;
      name?: string;
      is_default?: boolean;
      retired_at?: string | null;
    }) => {
      const { data } = await apiClient.patch(`/people/${id}`, body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['people'] }),
  });
}

export function useDeletePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/people/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['people'] }),
  });
}
