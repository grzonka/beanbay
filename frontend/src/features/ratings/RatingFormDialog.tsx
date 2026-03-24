import apiClient from '@/api/client';
import AutocompleteCreate from '@/components/AutocompleteCreate';
import FlavorTagSelect from '@/components/FlavorTagSelect';
import { useNotification } from '@/components/NotificationProvider';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Slider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

interface Person {
  id: string;
  name: string;
}
interface FlavorTag {
  id: string;
  name: string;
}

interface CreatePersonForm {
  initialName: string;
  onCreated: (person: Person) => void;
  onCancel: () => void;
}

function CreatePersonInlineForm({
  initialName,
  onCreated,
  onCancel,
}: CreatePersonForm) {
  const [name, setName] = useState(initialName);
  const { notify } = useNotification();

  const handleSubmit = async () => {
    const { data } = await apiClient.post<Person>('/people', { name });
    notify('Person created');
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

interface SliderFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
}

function SliderField({ label, value, onChange }: SliderFieldProps) {
  return (
    <Box>
      <Typography gutterBottom variant="body2">
        {label}: <strong>{value}</strong>
      </Typography>
      <Slider
        value={value}
        onChange={(_, v) => onChange(v as number)}
        min={0}
        max={10}
        step={1}
        marks
        valueLabelDisplay="auto"
        size="small"
      />
    </Box>
  );
}

interface RatingFormDialogProps {
  open: boolean;
  onClose: () => void;
  beanId: string;
}

export default function RatingFormDialog({
  open,
  onClose,
  beanId,
}: RatingFormDialogProps) {
  const { notify } = useNotification();
  const qc = useQueryClient();

  const [person, setPerson] = useState<Person | null>(null);
  const [personError, setPersonError] = useState(false);
  const [isPending, setIsPending] = useState(false);

  const { data: peopleData } = useQuery({
    queryKey: ['people', 'default'],
    queryFn: async () => {
      const { data } = await apiClient.get('/people', {
        params: { limit: 50 },
      });
      return data;
    },
  });

  useEffect(() => {
    if (!person && peopleData?.items) {
      const defaultPerson = peopleData.items.find((p: any) => p.is_default);
      if (defaultPerson) {
        setPerson({ id: defaultPerson.id, name: defaultPerson.name });
      }
    }
  }, [peopleData, person]);

  // Taste fields
  const [score, setScore] = useState(5);
  const [acidity, setAcidity] = useState(5);
  const [sweetness, setSweetness] = useState(5);
  const [body, setBody] = useState(5);
  const [complexity, setComplexity] = useState(5);
  const [aroma, setAroma] = useState(5);
  const [cleanCup, setCleanCup] = useState(5);
  const [notes, setNotes] = useState('');
  const [flavorTags, setFlavorTags] = useState<FlavorTag[]>([]);

  const resetForm = () => {
    const defaultPerson = peopleData?.items?.find((p: any) => p.is_default);
    setPerson(
      defaultPerson ? { id: defaultPerson.id, name: defaultPerson.name } : null,
    );
    setPersonError(false);
    setScore(5);
    setAcidity(5);
    setSweetness(5);
    setBody(5);
    setComplexity(5);
    setAroma(5);
    setCleanCup(5);
    setNotes('');
    setFlavorTags([]);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    if (!person) {
      setPersonError(true);
      return;
    }
    setIsPending(true);
    try {
      await apiClient.post(`/beans/${beanId}/ratings`, {
        person_id: person.id,
        taste: {
          score,
          acidity,
          sweetness,
          body,
          complexity,
          aroma,
          clean_cup: cleanCup,
          notes: notes || null,
          flavor_tag_ids: flavorTags.map((t) => t.id),
        },
      });
      qc.invalidateQueries({ queryKey: ['beans', beanId, 'ratings'] });
      notify('Rating added');
      handleClose();
    } finally {
      setIsPending(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Rating</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <AutocompleteCreate<Person>
            label="Person"
            queryKey={['people']}
            fetchFn={async (q) => {
              const { data } = await apiClient.get('/people', {
                params: { q, limit: 50 },
              });
              return data;
            }}
            value={person}
            onChange={(v) => {
              setPerson(v as Person | null);
              if (v) setPersonError(false);
            }}
            required
            error={personError}
            helperText={personError ? 'Person is required' : undefined}
            renderCreateForm={(props) => <CreatePersonInlineForm {...props} />}
          />

          <Divider>
            <Typography variant="caption" color="text.secondary">
              Taste
            </Typography>
          </Divider>

          <SliderField label="Score" value={score} onChange={setScore} />
          <SliderField label="Acidity" value={acidity} onChange={setAcidity} />
          <SliderField
            label="Sweetness"
            value={sweetness}
            onChange={setSweetness}
          />
          <SliderField label="Body" value={body} onChange={setBody} />
          <SliderField
            label="Complexity"
            value={complexity}
            onChange={setComplexity}
          />
          <SliderField label="Aroma" value={aroma} onChange={setAroma} />
          <SliderField
            label="Clean Cup"
            value={cleanCup}
            onChange={setCleanCup}
          />

          <TextField
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            rows={3}
          />

          <FlavorTagSelect value={flavorTags} onChange={setFlavorTags} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!person || isPending}
        >
          Add Rating
        </Button>
      </DialogActions>
    </Dialog>
  );
}
