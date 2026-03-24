import { useNotification } from '@/components/NotificationProvider';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import { Button, CircularProgress } from '@mui/material';
import { type Recommendation, useSuggest } from '../hooks';

interface Props {
  beanId: string;
  brewSetupId: string;
  personId?: string;
  onSuggestion: (rec: Recommendation, campaignId: string) => void;
  disabled?: boolean;
}

export default function SuggestButton({
  beanId,
  brewSetupId,
  personId,
  onSuggestion,
  disabled,
}: Props) {
  const suggest = useSuggest();
  const { notify } = useNotification();

  const handleClick = async () => {
    try {
      const rec = await suggest.mutateAsync({
        bean_id: beanId,
        brew_setup_id: brewSetupId,
        person_id: personId,
      });
      onSuggestion(rec, rec.campaign_id);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Suggestion failed', 'error');
    }
  };

  return (
    <Button
      variant="outlined"
      startIcon={
        suggest.isPending ? <CircularProgress size={18} /> : <AutoFixHighIcon />
      }
      onClick={handleClick}
      disabled={disabled || suggest.isPending || !beanId || !brewSetupId}
    >
      {suggest.isPending ? 'Computing...' : 'Get Suggestion'}
    </Button>
  );
}
