import apiClient from '@/api/client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface CampaignListItem {
  id: string;
  bean_name: string;
  brew_setup_name: string;
  phase: string;
  measurement_count: number;
  best_score: number | null;
  created_at: string;
}

export interface EffectiveRange {
  parameter_name: string;
  min_value: number | null;
  max_value: number | null;
  step: number | null;
  allowed_values: (string | number)[] | null;
  source: string;
}

export interface CampaignDetail extends CampaignListItem {
  bean_id: string;
  brew_setup_id: string;
  updated_at: string;
  effective_ranges: EffectiveRange[];
  convergence: ConvergenceInfo | null;
  score_history: ScoreHistoryEntry[];
}

export interface ScoreHistoryEntry {
  shot_number: number;
  score: number;
  is_failed: boolean;
  phase: string;
}

export interface ConvergenceInfo {
  status: string;
  improvement_rate: number | null;
}

export interface CampaignProgress {
  phase: string;
  measurement_count: number;
  best_score: number | null;
  convergence: ConvergenceInfo;
  score_history: ScoreHistoryEntry[];
}

export interface PosteriorMeasurement {
  values: Record<string, number>;
  score: number;
}

export interface PosteriorData {
  params: string[];
  grid: number[][];
  mean: number[] | number[][];
  std: number[] | number[][];
  measurements: PosteriorMeasurement[];
}

export interface FeatureImportanceData {
  parameters: string[];
  importance: number[];
  measurement_count: number;
}

export interface Recommendation {
  id: string;
  campaign_id: string;
  brew_id: string | null;
  phase: string;
  predicted_score: number | null;
  predicted_std: number | null;
  parameter_values: Record<string, unknown>;
  status: string;
  created_at: string;
  optimization_mode: string | null;
  personal_brew_count: number | null;
}

export interface PersonPreferences {
  person: { id: string; name: string };
  brew_stats: Record<string, unknown>;
  top_beans: Record<string, unknown>[];
  flavor_profile: Record<string, number>;
  roast_preference: Record<string, unknown>;
  origin_preferences: Record<string, unknown>[];
  method_breakdown: Record<string, unknown>[];
  taste_profile: {
    acidity: number | null;
    sweetness: number | null;
    body: number | null;
    bitterness: number | null;
    balance: number | null;
    aftertaste: number | null;
  } | null;
  taste_profile_brew_count: number;
}

// ─── Query Hooks ─────────────────────────────────────────────────────────────

export function useCampaigns() {
  return useQuery<CampaignListItem[]>({
    queryKey: ['optimize', 'campaigns'],
    queryFn: async () => {
      const { data } = await apiClient.get('/optimize/campaigns');
      return data;
    },
  });
}

export function useCampaignDetail(campaignId: string) {
  return useQuery<CampaignDetail>({
    queryKey: ['optimize', 'campaigns', campaignId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/optimize/campaigns/${campaignId}`);
      return data;
    },
    enabled: !!campaignId,
  });
}

export function useCampaignProgress(campaignId: string) {
  return useQuery<CampaignProgress>({
    queryKey: ['optimize', 'campaigns', campaignId, 'progress'],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/optimize/campaigns/${campaignId}/progress`,
      );
      return data;
    },
    enabled: !!campaignId,
  });
}

export function usePosterior(
  campaignId: string,
  params: string,
  points?: number,
) {
  return useQuery<PosteriorData>({
    queryKey: [
      'optimize',
      'campaigns',
      campaignId,
      'posterior',
      params,
      points,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/optimize/campaigns/${campaignId}/posterior`,
        {
          params: { params, points },
        },
      );
      return data;
    },
    enabled: !!campaignId,
    retry: false,
  });
}

export function useFeatureImportance(campaignId: string) {
  return useQuery<FeatureImportanceData>({
    queryKey: ['optimize', 'campaigns', campaignId, 'feature-importance'],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/optimize/campaigns/${campaignId}/feature-importance`,
      );
      return data;
    },
    enabled: !!campaignId,
  });
}

export function useCampaignRecommendations(campaignId: string) {
  return useQuery<Recommendation[]>({
    queryKey: ['optimize', 'campaigns', campaignId, 'recommendations'],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/optimize/campaigns/${campaignId}/recommendations`,
      );
      return data;
    },
    enabled: !!campaignId,
  });
}

export function usePersonPreferences(personId: string) {
  return useQuery<PersonPreferences>({
    queryKey: ['optimize', 'people', personId, 'preferences'],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/optimize/people/${personId}/preferences`,
      );
      return data;
    },
    enabled: !!personId,
  });
}

// ─── Mutation Hooks ───────────────────────────────────────────────────────────

interface SuggestParams {
  bean_id: string;
  brew_setup_id: string;
  person_id?: string;
  mode?: string;
}

interface JobStatus {
  job_id: string;
  status: string;
  result_id: string | null;
  error_message: string | null;
}

async function pollJobUntilDone(
  jobId: string,
  maxAttempts = 30,
  delayMs = 1000,
): Promise<JobStatus> {
  for (let i = 0; i < maxAttempts; i++) {
    const { data } = await apiClient.get<JobStatus>(`/optimize/jobs/${jobId}`);
    if (data.status === 'completed' || data.status === 'failed') {
      return data;
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  throw new Error('Job timed out');
}

export function useSuggest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: SuggestParams): Promise<Recommendation> => {
      // Step 1: Create or find campaign
      const { data: campaign } = await apiClient.post(
        '/optimize/campaigns',
        params,
      );

      // Step 2: Request a recommendation
      const { data: jobRef } = await apiClient.post(
        `/optimize/campaigns/${campaign.id}/recommend`,
        { person_id: params.person_id, mode: params.mode ?? 'auto' },
      );

      // Step 3: Poll job until done
      const job = await pollJobUntilDone(jobRef.job_id);
      if (job.status === 'failed' || !job.result_id) {
        throw new Error(job.error_message || 'Recommendation job failed');
      }

      // Step 4: Fetch the completed recommendation
      const { data: recommendation } = await apiClient.get<Recommendation>(
        `/optimize/recommendations/${job.result_id}`,
      );
      return recommendation;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['optimize', 'campaigns'] });
      qc.invalidateQueries({
        queryKey: ['optimize', 'campaigns', variables.bean_id],
      });
    },
  });
}

export function useLinkRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, brew_id }: { id: string; brew_id: string }) => {
      const { data } = await apiClient.post(
        `/optimize/recommendations/${id}/link`,
        { brew_id },
      );
      return data as Recommendation;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: ['optimize', 'campaigns', data.campaign_id],
      });
      qc.invalidateQueries({
        queryKey: [
          'optimize',
          'campaigns',
          data.campaign_id,
          'recommendations',
        ],
      });
    },
  });
}
