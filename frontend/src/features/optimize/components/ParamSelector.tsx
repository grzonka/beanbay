import { Box, FormControl, InputLabel, MenuItem, Select } from '@mui/material';

interface Props {
  params: string[];
  xValue: string;
  yValue: string;
  onXChange: (v: string) => void;
  onYChange: (v: string) => void;
}

export default function ParamSelector({
  params,
  xValue,
  yValue,
  onXChange,
  onYChange,
}: Props) {
  return (
    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
      <FormControl size="small" sx={{ minWidth: 160 }}>
        <InputLabel>X Axis</InputLabel>
        <Select
          value={xValue}
          label="X Axis"
          onChange={(e) => onXChange(e.target.value)}
        >
          {params.map((p) => (
            <MenuItem key={p} value={p}>
              {p.replace(/_/g, ' ')}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl size="small" sx={{ minWidth: 160 }}>
        <InputLabel>Y Axis</InputLabel>
        <Select
          value={yValue}
          label="Y Axis"
          onChange={(e) => onYChange(e.target.value)}
        >
          {params.map((p) => (
            <MenuItem key={p} value={p}>
              {p.replace(/_/g, ' ')}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}
