import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useQuery } from '@tanstack/react-query';

export interface BagListItem {
  id: string;
  bean_id: string;
  bean_name: string | null;
  roast_date: string | null;
  opened_at: string | null;
  weight: number;
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

export function useAllBags(params: PaginationParams & { bean_id?: string }) {
  return useQuery<{ items: BagListItem[]; total: number }>({
    queryKey: ['bags', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/bags', { params });
      return data;
    },
  });
}
