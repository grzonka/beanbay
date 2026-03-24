import apiClient from '@/api/client';
import { useNotification } from '@/components/NotificationProvider';
import type { Grinder } from '@/features/equipment/hooks';
import SuggestButton from '@/features/optimize/components/SuggestButton';
import {
  type Recommendation,
  useLinkRecommendation,
  useSuggest,
} from '@/features/optimize/hooks';
import { validateGrindDisplay } from '@/utils/grindValidation';
import {
  Box,
  Button,
  Paper,
  Step,
  StepLabel,
  Stepper,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
// frontend/src/features/brews/components/BrewWizard.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useCreateBrew } from '../hooks';
import BrewStepParams, { type ParamsData } from './BrewStepParams';
import BrewStepSetup, { type SetupData } from './BrewStepSetup';
import BrewStepTaste, { type TasteData } from './BrewStepTaste';

const STEPS = ['Setup', 'Parameters', 'Taste'];

function nowLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

interface WizardState {
  setup: SetupData;
  params: ParamsData;
  taste: TasteData;
}

const initialState: WizardState = {
  setup: {
    bag: null,
    brew_setup: null,
    person: null,
  },
  params: {
    grind_setting_display: '',
    temperature: '',
    pressure: '',
    flow_rate: '',
    dose: '',
    yield_amount: '',
    pre_infusion_time: '',
    total_time: '',
    stop_mode: null,
    is_failed: false,
    notes: '',
    brewed_at: nowLocal(),
  },
  taste: {
    score: 0,
    acidity: null,
    sweetness: null,
    body: null,
    bitterness: null,
    balance: null,
    aftertaste: null,
    notes: '',
    flavor_tags: [],
  },
};

function hasTasteData(taste: TasteData): boolean {
  return (
    taste.score != null ||
    taste.acidity != null ||
    taste.sweetness != null ||
    taste.body != null ||
    taste.bitterness != null ||
    taste.balance != null ||
    taste.aftertaste != null ||
    taste.notes.trim() !== '' ||
    taste.flavor_tags.length > 0
  );
}

export default function BrewWizard() {
  const navigate = useNavigate();
  const { notify } = useNotification();
  const createBrew = useCreateBrew();

  const [activeStep, setActiveStep] = useState(0);
  const [state, setState] = useState<WizardState>(initialState);
  const [suggestion, setSuggestion] = useState<{
    recommendation: Recommendation;
    campaignId: string;
  } | null>(null);

  const linkRec = useLinkRecommendation();
  const suggest = useSuggest();

  const grinderId = state.setup.brew_setup?.grinder_id ?? null;
  const { data: grinder } = useQuery<Grinder | null>({
    queryKey: ['grinders', grinderId],
    queryFn: async () => {
      if (!grinderId) return null;
      const { data } = await apiClient.get(`/grinders/${grinderId}`);
      return data;
    },
    enabled: !!grinderId,
  });

  const patchSetup = (patch: Partial<SetupData>) =>
    setState((prev) => ({ ...prev, setup: { ...prev.setup, ...patch } }));

  const patchParams = (patch: Partial<ParamsData>) =>
    setState((prev) => ({ ...prev, params: { ...prev.params, ...patch } }));

  const patchTaste = (patch: Partial<TasteData>) =>
    setState((prev) => ({ ...prev, taste: { ...prev.taste, ...patch } }));

  const handleSuggestion = (rec: Recommendation, campaignId: string) => {
    setSuggestion({ recommendation: rec, campaignId });
    const vals = rec.parameter_values;
    const patch: Partial<ParamsData> = {};
    if (vals.temperature != null) patch.temperature = String(vals.temperature);
    if (vals.dose != null) patch.dose = String(vals.dose);
    if (vals.yield_amount != null)
      patch.yield_amount = String(vals.yield_amount);
    if (vals.pressure != null) patch.pressure = String(vals.pressure);
    if (vals.flow_rate != null) patch.flow_rate = String(vals.flow_rate);
    if (vals.pre_infusion_time != null)
      patch.pre_infusion_time = String(vals.pre_infusion_time);
    if (vals.grind_setting_display != null)
      patch.grind_setting_display = String(vals.grind_setting_display);
    if (vals.total_time != null) patch.total_time = String(vals.total_time);
    // bloom_weight and other non-ParamsData fields are intentionally skipped
    patchParams(patch);
  };

  const handleToggleMode = async () => {
    if (!state.setup.bag || !state.setup.brew_setup) return;
    const currentMode = suggestion?.recommendation.optimization_mode;
    const newMode = currentMode === 'personal' ? 'community' : 'personal';
    try {
      const rec = await suggest.mutateAsync({
        bean_id: state.setup.bag.bean_id,
        brew_setup_id: state.setup.brew_setup.id,
        person_id: state.setup.person?.id,
        mode: newMode,
      });
      handleSuggestion(rec, rec.campaign_id);
    } catch {
      // Keep current suggestion on failure
    }
  };

  // Step validation
  const step0Valid =
    state.setup.bag != null &&
    state.setup.brew_setup != null &&
    state.setup.person != null;

  const rings = grinder?.rings ?? undefined;
  const grindValidationError = rings
    ? validateGrindDisplay(state.params.grind_setting_display, rings)
    : null;

  const step1Valid =
    state.params.dose.trim() !== '' &&
    Number(state.params.dose) > 0 &&
    grindValidationError === null;

  const canNext =
    activeStep === 0 ? step0Valid : activeStep === 1 ? step1Valid : true;

  const handleNext = () => setActiveStep((s) => s + 1);
  const handleBack = () => setActiveStep((s) => s - 1);

  const buildBody = (includeTaste: boolean): Record<string, unknown> => {
    const { setup, params, taste } = state;

    const body: Record<string, unknown> = {
      bag_id: setup.bag?.id,
      brew_setup_id: setup.brew_setup?.id,
      person_id: setup.person?.id,
      dose: Number(params.dose),
      is_failed: params.is_failed,
      brewed_at: params.brewed_at || null,
    };

    if (params.grind_setting_display.trim())
      body.grind_setting_display = params.grind_setting_display.trim();
    if (params.temperature.trim())
      body.temperature = Number(params.temperature);
    if (params.pressure.trim()) body.pressure = Number(params.pressure);
    if (params.flow_rate.trim()) body.flow_rate = Number(params.flow_rate);
    if (params.yield_amount.trim())
      body.yield_amount = Number(params.yield_amount);
    if (params.pre_infusion_time.trim())
      body.pre_infusion_time = Number(params.pre_infusion_time);
    if (params.total_time.trim()) body.total_time = Number(params.total_time);
    if (params.stop_mode) body.stop_mode_id = params.stop_mode.id;
    if (params.notes.trim()) body.notes = params.notes.trim();

    if (includeTaste && hasTasteData(taste)) {
      const tasteBody: Record<string, unknown> = {};
      if (taste.score != null) tasteBody.score = taste.score;
      if (taste.acidity != null) tasteBody.acidity = taste.acidity;
      if (taste.sweetness != null) tasteBody.sweetness = taste.sweetness;
      if (taste.body != null) tasteBody.body = taste.body;
      if (taste.bitterness != null) tasteBody.bitterness = taste.bitterness;
      if (taste.balance != null) tasteBody.balance = taste.balance;
      if (taste.aftertaste != null) tasteBody.aftertaste = taste.aftertaste;
      if (taste.notes.trim()) tasteBody.notes = taste.notes.trim();
      if (taste.flavor_tags.length > 0)
        tasteBody.flavor_tag_ids = taste.flavor_tags.map((t) => t.id);
      body.taste = tasteBody;
    }

    return body;
  };

  const handleSubmit = async (includeTaste: boolean) => {
    const body = buildBody(includeTaste);
    const newBrew = await createBrew.mutateAsync(body);

    if (suggestion) {
      try {
        await linkRec.mutateAsync({
          id: suggestion.recommendation.id,
          brew_id: newBrew.id,
        });
      } catch {
        // Non-critical — don't block navigation
      }
    }

    notify('Brew logged successfully!');
    navigate(`/brews/${newBrew.id}`);
  };

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto', mt: 2 }}>
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Log a Brew
      </Typography>

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <Paper variant="outlined" sx={{ p: 3 }}>
        {activeStep === 0 && (
          <BrewStepSetup data={state.setup} onChange={patchSetup} />
        )}
        {activeStep === 1 && (
          <BrewStepParams
            data={state.params}
            onChange={patchParams}
            rings={rings}
            suggestion={suggestion?.recommendation ?? null}
            onToggleMode={suggestion ? handleToggleMode : undefined}
            suggestButton={
              state.setup.bag && state.setup.brew_setup ? (
                <SuggestButton
                  beanId={state.setup.bag.bean_id}
                  brewSetupId={state.setup.brew_setup.id}
                  personId={state.setup.person?.id}
                  onSuggestion={handleSuggestion}
                />
              ) : undefined
            }
          />
        )}
        {activeStep === 2 && (
          <BrewStepTaste data={state.taste} onChange={patchTaste} />
        )}
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button
          onClick={handleBack}
          disabled={activeStep === 0 || createBrew.isPending}
        >
          Back
        </Button>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {activeStep === 2 && (
            <Button
              variant="outlined"
              onClick={() => handleSubmit(false)}
              disabled={createBrew.isPending}
            >
              Skip &amp; Save
            </Button>
          )}

          {activeStep < 2 ? (
            <Button
              variant="contained"
              onClick={handleNext}
              disabled={!canNext}
            >
              Next
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={() => handleSubmit(true)}
              disabled={createBrew.isPending}
            >
              {createBrew.isPending ? 'Saving…' : 'Save Brew'}
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
}
