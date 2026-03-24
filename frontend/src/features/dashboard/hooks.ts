import apiClient from '@/api/client';
import type { BrewListItem } from '@/features/brews/hooks';
import { useQuery } from '@tanstack/react-query';

export interface BrewStats {
  total: number;
  this_week: number;
  this_month: number;
  total_failed: number;
  fail_rate: number | null;
  avg_dose_g: number | null;
  avg_yield_g: number | null;
  avg_brew_time_s: number | null;
  last_brewed_at: string | null;
  by_method: {
    brew_method_id: string;
    brew_method_name: string;
    count: number;
  }[];
}

export interface BeanStats {
  total_beans: number;
  beans_active: number;
  mix_type_breakdown: Record<string, number>;
  use_type_breakdown: Record<string, number>;
  top_roasters: { roaster_id: string; roaster_name: string; count: number }[];
  top_origins: { origin_id: string; origin_name: string; count: number }[];
  total_bags: number;
  bags_active: number;
  bags_unopened: number;
  avg_bag_weight_g: number | null;
  avg_bag_price: number | null;
}

export interface TasteStats {
  brew_taste: {
    total_rated: number;
    avg_axes: Record<string, number | null>;
    best_score: number | null;
    best_brew_id: string | null;
    top_flavor_tags: {
      flavor_tag_id: string;
      flavor_tag_name: string;
      count: number;
    }[];
  };
  bean_taste: {
    total_rated: number;
    avg_axes: Record<string, number | null>;
    best_score: number | null;
    best_bean_id: string | null;
    top_flavor_tags: {
      flavor_tag_id: string;
      flavor_tag_name: string;
      count: number;
    }[];
  };
}

export interface EquipmentStats {
  total_grinders: number;
  total_brewers: number;
  total_papers: number;
  total_waters: number;
  top_grinders: { id: string; name: string; brew_count: number }[];
  top_brewers: { id: string; name: string; brew_count: number }[];
  top_setups: { id: string; name: string | null; brew_count: number }[];
  most_used_method: { id: string; name: string; brew_count: number } | null;
}

export interface CuppingStats {
  total: number;
  avg_total_score: number | null;
  best_total_score: number | null;
  best_cupping_id: string | null;
  top_flavor_tags: {
    flavor_tag_id: string;
    flavor_tag_name: string;
    count: number;
  }[];
}

export const useBrewStats = () =>
  useQuery<BrewStats>({
    queryKey: ['stats', 'brews'],
    queryFn: async () => {
      const { data } = await apiClient.get('/stats/brews');
      return data;
    },
  });
export const useBeanStats = () =>
  useQuery<BeanStats>({
    queryKey: ['stats', 'beans'],
    queryFn: async () => {
      const { data } = await apiClient.get('/stats/beans');
      return data;
    },
  });
export const useTasteStats = () =>
  useQuery<TasteStats>({
    queryKey: ['stats', 'taste'],
    queryFn: async () => {
      const { data } = await apiClient.get('/stats/taste');
      return data;
    },
  });
export const useEquipmentStats = () =>
  useQuery<EquipmentStats>({
    queryKey: ['stats', 'equipment'],
    queryFn: async () => {
      const { data } = await apiClient.get('/stats/equipment');
      return data;
    },
  });
export const useCuppingStats = () =>
  useQuery<CuppingStats>({
    queryKey: ['stats', 'cuppings'],
    queryFn: async () => {
      const { data } = await apiClient.get('/stats/cuppings');
      return data;
    },
  });

export const useRecentBrews = () =>
  useQuery<{ items: BrewListItem[]; total: number }>({
    queryKey: ['brews', { limit: 5, sort_by: 'brewed_at', sort_dir: 'desc' }],
    queryFn: async () => {
      const { data } = await apiClient.get('/brews', {
        params: { limit: 5, sort_by: 'brewed_at', sort_dir: 'desc' },
      });
      return data;
    },
  });
