import apiClient from '@/api/client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface BeanTaste {
  id: string;
  bean_rating_id: string;
  score: number | null;
  acidity: number | null;
  sweetness: number | null;
  body: number | null;
  complexity: number | null;
  aroma: number | null;
  clean_cup: number | null;
  notes: string | null;
  flavor_tags: { id: string; name: string }[];
  created_at: string;
  updated_at: string;
}

export interface BeanRating {
  id: string;
  bean_id: string;
  person_id: string;
  person_name: string;
  rated_at: string;
  taste: BeanTaste | null;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

export function useRating(id: string) {
  return useQuery<BeanRating>({
    queryKey: ['bean-ratings', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/bean-ratings/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useDeleteRating() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/bean-ratings/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bean-ratings'] }),
  });
}

export function useUpsertBeanTaste(ratingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.put(
        `/bean-ratings/${ratingId}/taste`,
        body,
      );
      return data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['bean-ratings', ratingId] }),
  });
}

export function useUpdateBeanTaste(ratingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await apiClient.patch(
        `/bean-ratings/${ratingId}/taste`,
        body,
      );
      return data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['bean-ratings', ratingId] }),
  });
}
