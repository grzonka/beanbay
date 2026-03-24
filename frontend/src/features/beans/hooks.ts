import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

// ---- TypeScript interfaces ----

export interface BeanOrigin {
  origin_id: string;
  origin_name: string;
  percentage: number | null;
}

export interface BeanProcess {
  id: string;
  name: string;
}

export interface BeanVariety {
  id: string;
  name: string;
}

export interface FlavorTag {
  id: string;
  name: string;
}

export interface Bag {
  id: string;
  bean_id: string;
  roast_date: string | null;
  opened_at: string | null;
  weight: number | null;
  price: number | null;
  is_preground: boolean;
  notes: string | null;
  bought_at: string | null;
  vendor_id: string | null;
  frozen_at: string | null;
  thawed_at: string | null;
  storage_type_id: string | null;
  best_date: string | null;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

export interface TasteProfile {
  aroma: number | null;
  acidity: number | null;
  sweetness: number | null;
  body: number | null;
  finish: number | null;
  score: number | null;
}

export interface BeanRating {
  id: string;
  bean_id: string;
  person_id: string | null;
  person_name: string | null;
  rated_at: string | null;
  taste: TasteProfile | null;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

export interface Bean {
  id: string;
  name: string;
  notes: string | null;
  roast_degree: number | null;
  bean_mix_type: string | null;
  bean_use_type: string | null;
  decaf: boolean;
  url: string | null;
  ean: string | null;
  roaster_id: string | null;
  roaster: { id: string; name: string } | null;
  origins: BeanOrigin[];
  processes: BeanProcess[];
  varieties: BeanVariety[];
  flavor_tags: FlavorTag[];
  bags: Bag[];
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

// ---- Paginated wrappers ----

interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---- Bean filter params ----

export interface BeanFilterParams extends PaginationParams {
  roaster_id?: string;
  origin_id?: string;
  process_id?: string;
  variety_id?: string;
}

// ---- Bean hooks ----

export function useBeans(params: BeanFilterParams) {
  return useQuery<Paginated<Bean>>({
    queryKey: ['beans', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/beans', { params });
      return data;
    },
  });
}

export function useBean(id: string) {
  return useQuery<Bean>({
    queryKey: ['beans', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/beans/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateBean() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.post('/beans', body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['beans'] }),
  });
}

export function useUpdateBean() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: { id: string; [key: string]: unknown }) => {
      const { data } = await apiClient.patch(`/beans/${id}`, body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['beans'] }),
  });
}

export function useDeleteBean() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/beans/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['beans'] }),
  });
}

// ---- Bag hooks (scoped to a bean) ----

export function useBags(beanId: string, params: PaginationParams) {
  return useQuery<Paginated<Bag>>({
    queryKey: ['beans', beanId, 'bags', params],
    queryFn: async () => {
      const { data } = await apiClient.get(`/beans/${beanId}/bags`, { params });
      return data;
    },
    enabled: !!beanId,
  });
}

export function useCreateBag(beanId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.post(`/beans/${beanId}/bags`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['beans', beanId, 'bags'] });
      qc.invalidateQueries({ queryKey: ['beans', beanId] });
    },
  });
}

export function useUpdateBag(beanId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: { id: string; [key: string]: unknown }) => {
      const { data } = await apiClient.patch(
        `/beans/${beanId}/bags/${id}`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['beans', beanId, 'bags'] });
      qc.invalidateQueries({ queryKey: ['beans', beanId] });
    },
  });
}

export function useDeleteBag(beanId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (bagId: string) => {
      await apiClient.delete(`/beans/${beanId}/bags/${bagId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['beans', beanId, 'bags'] });
      qc.invalidateQueries({ queryKey: ['beans', beanId] });
    },
  });
}

// ---- Bean Rating hooks (scoped to a bean) ----

export function useBeanRatings(beanId: string, params: PaginationParams) {
  return useQuery<Paginated<BeanRating>>({
    queryKey: ['beans', beanId, 'ratings', params],
    queryFn: async () => {
      const { data } = await apiClient.get(`/beans/${beanId}/ratings`, {
        params,
      });
      return data;
    },
    enabled: !!beanId,
  });
}

export function useCreateBeanRating(beanId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.post(`/beans/${beanId}/ratings`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['beans', beanId, 'ratings'] });
    },
  });
}
