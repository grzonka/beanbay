import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface BrewListItem {
  id: string;
  grind_setting: number | null;
  grind_setting_display: string | null;
  dose: number;
  yield_amount: number | null;
  temperature: number | null;
  is_failed: boolean;
  brewed_at: string;
  created_at: string;
  bean_name: string;
  brew_method_name: string;
  person_name: string;
  score: number | null;
}

export interface BrewTaste {
  id: string;
  brew_id: string;
  score: number | null;
  acidity: number | null;
  sweetness: number | null;
  body: number | null;
  bitterness: number | null;
  balance: number | null;
  aftertaste: number | null;
  notes: string | null;
  flavor_tags: { id: string; name: string }[];
  created_at: string;
  updated_at: string;
}

export interface Brew {
  id: string;
  bag_id: string;
  brew_setup_id: string;
  person_id: string;
  grind_setting: number | null;
  grind_setting_display: string | null;
  temperature: number | null;
  pressure: number | null;
  flow_rate: number | null;
  dose: number;
  yield_amount: number | null;
  pre_infusion_time: number | null;
  total_time: number | null;
  stop_mode_id: string | null;
  is_failed: boolean;
  notes: string | null;
  brewed_at: string;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
  bag: { bean_name: string } | null;
  brew_setup: {
    id: string;
    name: string | null;
    brew_method_name: string | null;
    grinder_id: string | null;
    grinder_name: string | null;
    brewer_name: string | null;
    paper_name: string | null;
    water_name: string | null;
  } | null;
  person: { name: string } | null;
  taste: BrewTaste | null;
  stop_mode: { name: string } | null;
}

interface BrewListParams extends PaginationParams {
  bag_id?: string;
  bean_id?: string;
  brew_setup_id?: string;
  person_id?: string;
  brewed_after?: string;
  brewed_before?: string;
}

export function useBrews(params: BrewListParams) {
  return useQuery<{ items: BrewListItem[]; total: number }>({
    queryKey: ['brews', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/brews', { params });
      return data;
    },
  });
}

export function useBrew(id: string) {
  return useQuery<Brew>({
    queryKey: ['brews', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/brews/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateBrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.post('/brews', body);
      return data as Brew;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brews'] });
      qc.invalidateQueries({ queryKey: ['stats', 'brews'] });
      qc.invalidateQueries({ queryKey: ['stats', 'taste'] });
    },
  });
}

export function useUpdateBrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: { id: string; [key: string]: unknown }) => {
      const { data } = await apiClient.patch(`/brews/${id}`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brews'] });
      qc.invalidateQueries({ queryKey: ['stats', 'brews'] });
      qc.invalidateQueries({ queryKey: ['stats', 'taste'] });
    },
  });
}

export function useDeleteBrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/brews/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brews'] });
      qc.invalidateQueries({ queryKey: ['stats', 'brews'] });
      qc.invalidateQueries({ queryKey: ['stats', 'taste'] });
    },
  });
}

export function useUpsertBrewTaste(brewId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.put(`/brews/${brewId}/taste`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brews', brewId] });
      qc.invalidateQueries({ queryKey: ['stats', 'taste'] });
    },
  });
}

export function useDeleteBrewTaste(brewId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.delete(`/brews/${brewId}/taste`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brews', brewId] });
      qc.invalidateQueries({ queryKey: ['stats', 'taste'] });
    },
  });
}
