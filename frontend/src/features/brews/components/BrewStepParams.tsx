import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import type { Recommendation } from '@/features/optimize/hooks';
import {
  type RingConfig,
  getGrindPlaceholder,
  getGrindRangeDisplay,
  validateGrindDisplay,
} from '@/utils/grindValidation';
import GroupsIcon from '@mui/icons-material/Groups';
import PeopleIcon from '@mui/icons-material/Person';
// frontend/src/features/brews/components/BrewStepParams.tsx
import {
  Alert,
  Box,
  Chip,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

interface OptionItem {
  id: string;
  name: string;
}

export interface ParamsData {
  grind_setting_display: string;
  temperature: string;
  pressure: string;
  flow_rate: string;
  dose: string;
  yield_amount: string;
  pre_infusion_time: string;
  total_time: string;
  stop_mode: OptionItem | null;
  is_failed: boolean;
  notes: string;
  brewed_at: string;
}

interface BrewStepParamsProps {
  data: ParamsData;
  onChange: (patch: Partial<ParamsData>) => void;
  rings?: RingConfig[];
  suggestion?: Recommendation | null;
  suggestButton?: React.ReactNode;
  onToggleMode?: () => void;
}

export default function BrewStepParams({
  data,
  onChange,
  rings,
  suggestion,
  suggestButton,
  onToggleMode,
}: BrewStepParamsProps) {
  const grindError =
    rings && data.grind_setting_display.trim()
      ? validateGrindDisplay(data.grind_setting_display, rings)
      : null;

  const mode = suggestion?.optimization_mode;
  const isPersonal = mode === 'personal';
  const modeLabel = isPersonal
    ? `Personal${suggestion?.personal_brew_count != null ? ` (${suggestion.personal_brew_count})` : ''}`
    : 'Community';
  const modeTooltip = isPersonal
    ? 'Using only your brews. Click to switch to community data.'
    : 'Using all brews for this bean + setup. Click to switch to your brews only.';

  return (
    <Stack spacing={2}>
      {suggestButton && <Box sx={{ mb: 2 }}>{suggestButton}</Box>}

      {suggestion && suggestion.predicted_score != null && (
        <Alert
          severity="info"
          sx={{ mb: 2 }}
          action={
            mode && onToggleMode ? (
              <Tooltip title={modeTooltip} arrow>
                <Chip
                  icon={isPersonal ? <PeopleIcon /> : <GroupsIcon />}
                  label={modeLabel}
                  size="small"
                  color={isPersonal ? 'success' : 'default'}
                  onClick={onToggleMode}
                  clickable
                  sx={{ mr: 1 }}
                />
              </Tooltip>
            ) : undefined
          }
        >
          Suggested by optimizer ({suggestion.phase} phase)
          {' — Predicted: ~'}
          {suggestion.predicted_score.toFixed(1)}
          {suggestion.predicted_std != null && (
            <>
              {' '}
              (
              {(suggestion.predicted_score - suggestion.predicted_std).toFixed(
                1,
              )}
              –
              {(suggestion.predicted_score + suggestion.predicted_std).toFixed(
                1,
              )}
              )
            </>
          )}
        </Alert>
      )}

      <Typography variant="body2" color="text.secondary">
        Enter brew parameters. Only dose is required.
      </Typography>

      <TextField
        label="Brewed At"
        type="datetime-local"
        value={data.brewed_at}
        onChange={(e) => onChange({ brewed_at: e.target.value })}
        slotProps={{ inputLabel: { shrink: true } }}
        fullWidth
      />

      <TextField
        label="Dose (g)"
        type="number"
        value={data.dose}
        onChange={(e) => onChange({ dose: e.target.value })}
        required
        slotProps={{ input: { inputProps: { step: 0.1, min: 0 } } }}
        fullWidth
      />

      <TextField
        label="Yield (g)"
        type="number"
        value={data.yield_amount}
        onChange={(e) => onChange({ yield_amount: e.target.value })}
        slotProps={{ input: { inputProps: { step: 0.1, min: 0 } } }}
        fullWidth
      />

      <TextField
        label="Grind Setting"
        value={data.grind_setting_display}
        onChange={(e) => onChange({ grind_setting_display: e.target.value })}
        fullWidth
        placeholder={rings ? getGrindPlaceholder(rings) : 'e.g. 18 clicks, 3.2'}
        helperText={
          grindError ??
          (rings ? `Range: ${getGrindRangeDisplay(rings)}` : undefined)
        }
        error={!!grindError}
      />

      <Stack direction="row" spacing={2}>
        <TextField
          label="Temperature (°C)"
          type="number"
          value={data.temperature}
          onChange={(e) => onChange({ temperature: e.target.value })}
          slotProps={{ input: { inputProps: { step: 0.5 } } }}
          fullWidth
        />
        <TextField
          label="Pressure (bar)"
          type="number"
          value={data.pressure}
          onChange={(e) => onChange({ pressure: e.target.value })}
          slotProps={{ input: { inputProps: { step: 0.1 } } }}
          fullWidth
        />
      </Stack>

      <Stack direction="row" spacing={2}>
        <TextField
          label="Flow Rate (ml/s)"
          type="number"
          value={data.flow_rate}
          onChange={(e) => onChange({ flow_rate: e.target.value })}
          slotProps={{ input: { inputProps: { step: 0.1 } } }}
          fullWidth
        />
        <TextField
          label="Pre-infusion (s)"
          type="number"
          value={data.pre_infusion_time}
          onChange={(e) => onChange({ pre_infusion_time: e.target.value })}
          slotProps={{ input: { inputProps: { step: 1, min: 0 } } }}
          fullWidth
        />
      </Stack>

      <TextField
        label="Total Time (s)"
        type="number"
        value={data.total_time}
        onChange={(e) => onChange({ total_time: e.target.value })}
        slotProps={{ input: { inputProps: { step: 1, min: 0 } } }}
        fullWidth
      />

      <AutocompleteCreate<OptionItem>
        label="Stop Mode"
        queryKey={['stop-modes']}
        fetchFn={async (q) => {
          const { data: d } = await apiClient.get('/stop-modes', {
            params: { q, limit: 50 },
          });
          return d;
        }}
        value={data.stop_mode}
        onChange={(v) => onChange({ stop_mode: v as OptionItem | null })}
      />

      <Box>
        <FormControlLabel
          control={
            <Switch
              checked={data.is_failed}
              onChange={(_, checked) => onChange({ is_failed: checked })}
              color="error"
            />
          }
          label="Mark as failed brew"
        />
      </Box>

      <TextField
        label="Notes"
        value={data.notes}
        onChange={(e) => onChange({ notes: e.target.value })}
        multiline
        rows={3}
        fullWidth
      />
    </Stack>
  );
}
