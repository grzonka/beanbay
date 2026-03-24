import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface BrewSetup {
  id: string;
  name: string | null;
  brew_method_id: string;
  grinder_id: string | null;
  brewer_id: string | null;
  paper_id: string | null;
  water_id: string | null;
  brew_method_name: string | null;
  grinder_name: string | null;
  brewer_name: string | null;
  paper_name: string | null;
  water_name: string | null;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

export function useBrewSetups(params: PaginationParams) {
  return useQuery<{ items: BrewSetup[]; total: number }>({
    queryKey: ['brew-setups', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/brew-setups', { params });
      return data;
    },
  });
}

export function useCreateBrewSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.post('/brew-setups', body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brew-setups'] }),
  });
}

export function useUpdateBrewSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: { id: string; [key: string]: unknown }) => {
      const { data } = await apiClient.patch(`/brew-setups/${id}`, body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brew-setups'] }),
  });
}

export function useDeleteBrewSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/brew-setups/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brew-setups'] }),
  });
}
