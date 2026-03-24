import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import { Button, Stack, TextField, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
// frontend/src/features/brews/components/BrewStepSetup.tsx
import { useEffect, useState } from 'react';

interface OptionItem {
  id: string;
  name: string;
}

interface BagOption extends OptionItem {
  bean_id: string;
  weight: number | null;
  roast_date: string | null;
}

interface BrewSetupOption extends OptionItem {
  brew_method_name: string | null;
  grinder_id: string | null;
}

export interface SetupData {
  bag: BagOption | null;
  brew_setup: BrewSetupOption | null;
  person: OptionItem | null;
}

interface BrewStepSetupProps {
  data: SetupData;
  onChange: (patch: Partial<SetupData>) => void;
}

function CreatePersonForm({
  initialName,
  onCreated,
  onCancel,
}: {
  initialName: string;
  onCreated: (item: OptionItem) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initialName);

  const handleSubmit = async () => {
    const { data } = await apiClient.post<OptionItem>('/people', { name });
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

export default function BrewStepSetup({ data, onChange }: BrewStepSetupProps) {
  // Fetch people to auto-select default
  const { data: peopleData } = useQuery<{
    items: { id: string; name: string; is_default?: boolean }[];
  }>({
    queryKey: ['people', { limit: 100 }],
    queryFn: async () => {
      const { data: d } = await apiClient.get('/people', {
        params: { limit: 100 },
      });
      return d;
    },
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!data.person && peopleData) {
      const defaultPerson = peopleData.items.find((p) => p.is_default);
      if (defaultPerson) {
        onChange({
          person: { id: defaultPerson.id, name: defaultPerson.name },
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [peopleData]);

  return (
    <Stack spacing={3}>
      <Typography variant="body2" color="text.secondary">
        Select the bag of beans, brew setup, and who is brewing.
      </Typography>

      <AutocompleteCreate<BagOption>
        label="Bag"
        queryKey={['bags']}
        fetchFn={async (q) => {
          const { data: d } = await apiClient.get('/bags', {
            params: { q, limit: 50 },
          });
          const items: BagOption[] = (d.items ?? []).map(
            (bag: {
              id: string;
              bean_id: string;
              bean_name: string | null;
              weight: number | null;
              roast_date: string | null;
            }) => ({
              id: bag.id,
              bean_id: bag.bean_id,
              weight: bag.weight,
              roast_date: bag.roast_date,
              name: [
                bag.bean_name ?? 'Unknown bean',
                bag.weight != null ? `${bag.weight}g` : null,
                bag.roast_date ? `roasted ${bag.roast_date}` : null,
              ]
                .filter(Boolean)
                .join(' — '),
            }),
          );
          return { items };
        }}
        value={data.bag}
        onChange={(v) => onChange({ bag: v as BagOption | null })}
        required
      />

      <AutocompleteCreate<BrewSetupOption>
        label="Brew Setup"
        queryKey={['brew-setups']}
        fetchFn={async (q) => {
          const { data: d } = await apiClient.get('/brew-setups', {
            params: { q, limit: 50 },
          });
          const items: BrewSetupOption[] = (d.items ?? []).map(
            (s: {
              id: string;
              name: string | null;
              brew_method_name: string | null;
              grinder_id: string | null;
            }) => ({
              id: s.id,
              brew_method_name: s.brew_method_name,
              grinder_id: s.grinder_id ?? null,
              name: s.name
                ? s.brew_method_name
                  ? `${s.name} — ${s.brew_method_name}`
                  : s.name
                : (s.brew_method_name ?? 'Unnamed setup'),
            }),
          );
          return { items };
        }}
        value={data.brew_setup}
        onChange={(v) => onChange({ brew_setup: v as BrewSetupOption | null })}
        required
      />

      <AutocompleteCreate<OptionItem>
        label="Person"
        queryKey={['people']}
        fetchFn={async (q) => {
          const { data: d } = await apiClient.get('/people', {
            params: { q, limit: 50 },
          });
          return d;
        }}
        value={data.person}
        onChange={(v) => onChange({ person: v as OptionItem | null })}
        required
        renderCreateForm={(props) => <CreatePersonForm {...props} />}
      />
    </Stack>
  );
}
