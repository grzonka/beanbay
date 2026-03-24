import {
  Autocomplete,
  type AutocompleteRenderGetTagProps,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  type FilterOptionsState,
  TextField,
  createFilterOptions,
} from '@mui/material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
// frontend/src/components/AutocompleteCreate.tsx
import { type ReactNode, useState } from 'react';

interface OptionType {
  id: string;
  name: string;
  inputValue?: string;
}

const filter = createFilterOptions<OptionType>();

interface AutocompleteCreateProps<T extends OptionType> {
  label: string;
  queryKey: string[];
  fetchFn: (q: string) => Promise<{ items: T[] }>;
  value: T | T[] | null;
  onChange: (value: T | T[] | null) => void;
  multiple?: boolean;
  renderCreateForm?: (props: {
    onCreated: (item: T) => void;
    onCancel: () => void;
    initialName: string;
  }) => ReactNode;
  error?: boolean;
  helperText?: string;
  required?: boolean;
}

export default function AutocompleteCreate<T extends OptionType>({
  label,
  queryKey,
  fetchFn,
  value,
  onChange,
  multiple = false,
  renderCreateForm,
  error,
  helperText,
  required,
}: AutocompleteCreateProps<T>) {
  const [inputValue, setInputValue] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [pendingName, setPendingName] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, inputValue],
    queryFn: () => fetchFn(inputValue),
    staleTime: 30_000,
  });

  const options = (data?.items ?? []) as T[];

  const handleCreated = (item: T) => {
    queryClient.invalidateQueries({ queryKey });
    if (multiple) {
      const current = (value ?? []) as T[];
      onChange([...current, item]);
    } else {
      onChange(item);
    }
    setCreateDialogOpen(false);
  };

  return (
    <>
      <Autocomplete<T, boolean, false, true>
        multiple={multiple as boolean}
        freeSolo
        options={options}
        loading={isLoading}
        getOptionLabel={(option) =>
          typeof option === 'string' ? option : option.name
        }
        isOptionEqualToValue={(option, val) => option.id === val.id}
        value={value as T & T[]}
        inputValue={inputValue}
        onInputChange={(_, newInput) => setInputValue(newInput)}
        onChange={(_, newValue) => {
          if (Array.isArray(newValue)) {
            const createItem = newValue.find(
              (v): v is T & { inputValue: string } =>
                typeof v !== 'string' && 'inputValue' in v && !!v.inputValue,
            );
            if (createItem && renderCreateForm) {
              setPendingName(createItem.inputValue);
              setCreateDialogOpen(true);
              return;
            }
            onChange(newValue.filter((v) => typeof v !== 'string') as T[]);
          } else if (
            newValue &&
            typeof newValue !== 'string' &&
            'inputValue' in newValue &&
            newValue.inputValue &&
            renderCreateForm
          ) {
            setPendingName(newValue.inputValue);
            setCreateDialogOpen(true);
          } else {
            onChange(
              typeof newValue === 'string' ? null : (newValue as T | null),
            );
          }
        }}
        filterOptions={(opts, params) => {
          const filtered = filter(
            opts as OptionType[],
            params as FilterOptionsState<OptionType>,
          ) as T[];
          if (
            renderCreateForm &&
            params.inputValue !== '' &&
            !opts.some((o) => o.name === params.inputValue)
          ) {
            filtered.push({
              id: '',
              name: `+ Create "${params.inputValue}"`,
              inputValue: params.inputValue,
            } as T);
          }
          return filtered;
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label={label}
            error={error}
            helperText={helperText}
            required={required}
          />
        )}
        renderTags={
          multiple
            ? (tagValues: T[], getTagProps: AutocompleteRenderGetTagProps) =>
                tagValues.map((option, index) => {
                  const { key, ...rest } = getTagProps({ index });
                  return (
                    <Chip
                      key={key}
                      label={option.name}
                      size="small"
                      {...rest}
                    />
                  );
                })
            : undefined
        }
      />
      {renderCreateForm && (
        <Dialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
        >
          <DialogTitle>Create {label}</DialogTitle>
          <DialogContent>
            {renderCreateForm({
              onCreated: handleCreated,
              onCancel: () => setCreateDialogOpen(false),
              initialName: pendingName,
            })}
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
