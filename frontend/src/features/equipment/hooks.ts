import apiClient from '@/api/client';
import type { PaginationParams } from '@/utils/pagination';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

// Paper interfaces
export interface Paper {
  id: string;
  name: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

// Water interfaces
export interface WaterMineral {
  id: string;
  mineral_name: string;
  ppm: number;
}

export interface Water {
  id: string;
  name: string;
  notes: string | null;
  minerals: WaterMineral[];
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

// Grinder interfaces
export interface RingConfig {
  label: string;
  min: number;
  max: number;
  step: number;
}

export interface GrindRange {
  min: number;
  max: number;
  step: number;
}

export interface Grinder {
  id: string;
  name: string;
  dial_type: string;
  rings: RingConfig[];
  grind_range: GrindRange | null;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

// Brewer interfaces
export interface Brewer {
  id: string;
  name: string;
  temp_control_type: string;
  temp_min: number | null;
  temp_max: number | null;
  temp_step: number | null;
  preinfusion_type: string;
  preinfusion_max_time: number | null;
  pressure_control_type: string;
  pressure_min: number | null;
  pressure_max: number | null;
  flow_control_type: string;
  saturation_flow_rate: number | null;
  has_bloom: boolean;
  tier: number;
  methods: { id: string; name: string }[];
  stop_modes: { id: string; name: string }[];
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  is_retired: boolean;
}

// Generic CRUD hooks factory
function createEquipmentHooks<T>(endpoint: string, queryKey: string) {
  return {
    useList: (params: PaginationParams) =>
      useQuery<{ items: T[]; total: number }>({
        queryKey: [queryKey, params],
        queryFn: async () => {
          const { data } = await apiClient.get(`/${endpoint}`, { params });
          return data;
        },
      }),
    useGet: (id: string) =>
      useQuery<T>({
        queryKey: [queryKey, id],
        queryFn: async () => {
          const { data } = await apiClient.get(`/${endpoint}/${id}`);
          return data;
        },
        enabled: !!id,
      }),
    useCreate: () => {
      const qc = useQueryClient();
      return useMutation({
        mutationFn: async (body: Record<string, unknown>) => {
          const { data } = await apiClient.post(`/${endpoint}`, body);
          return data as T;
        },
        onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
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
          return data as T;
        },
        onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
      });
    },
    useDelete: () => {
      const qc = useQueryClient();
      return useMutation({
        mutationFn: async (id: string) => {
          await apiClient.delete(`/${endpoint}/${id}`);
        },
        onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
      });
    },
  };
}

export const paperHooks = createEquipmentHooks<Paper>('papers', 'papers');
export const waterHooks = createEquipmentHooks<Water>('waters', 'waters');
export const grinderHooks = createEquipmentHooks<Grinder>(
  'grinders',
  'grinders',
);
export const brewerHooks = createEquipmentHooks<Brewer>('brewers', 'brewers');
