import apiClient from '@/api/client';
// frontend/src/components/FlavorTagSelect.tsx
import AutocompleteCreate from '@/components/AutocompleteCreate';
import { useNotification } from '@/components/NotificationProvider';
import { Button, Stack, TextField } from '@mui/material';
import { useState } from 'react';

interface FlavorTag {
  id: string;
  name: string;
}

interface FlavorTagSelectProps {
  value: FlavorTag[];
  onChange: (tags: FlavorTag[]) => void;
  error?: boolean;
  helperText?: string;
}

function CreateFlavorTagForm({
  initialName,
  onCreated,
  onCancel,
}: {
  initialName: string;
  onCreated: (tag: FlavorTag) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initialName);
  const { notify } = useNotification();

  const handleSubmit = async () => {
    const { data } = await apiClient.post<FlavorTag>('/flavor-tags', { name });
    notify('Flavor tag created');
    onCreated(data);
  };

  return (
    <Stack spacing={2} sx={{ pt: 1 }}>
      <TextField
        label="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        autoFocus
      />
      <Stack direction="row" spacing={1} justifyContent="flex-end">
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!name.trim()}
        >
          Create
        </Button>
      </Stack>
    </Stack>
  );
}

export default function FlavorTagSelect({
  value,
  onChange,
  error,
  helperText,
}: FlavorTagSelectProps) {
  return (
    <AutocompleteCreate<FlavorTag>
      label="Flavor Tags"
      queryKey={['flavor-tags']}
      fetchFn={async (q) => {
        const { data } = await apiClient.get('/flavor-tags', {
          params: { q, limit: 50 },
        });
        return data;
      }}
      value={value}
      onChange={(v) => onChange((v ?? []) as FlavorTag[])}
      multiple
      error={error}
      helperText={helperText}
      renderCreateForm={(props) => <CreateFlavorTagForm {...props} />}
    />
  );
}
