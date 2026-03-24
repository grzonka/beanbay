import AppLayout from '@/layouts/AppLayout';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import { Suspense, lazy } from 'react';
import { Link, Route, Routes } from 'react-router';

const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'));
const BeansListPage = lazy(
  () => import('@/features/beans/pages/BeansListPage'),
);
const BeanDetailPage = lazy(
  () => import('@/features/beans/pages/BeanDetailPage'),
);
const BrewsListPage = lazy(
  () => import('@/features/brews/pages/BrewsListPage'),
);
const BrewWizard = lazy(() => import('@/features/brews/components/BrewWizard'));
const BrewDetailPage = lazy(
  () => import('@/features/brews/pages/BrewDetailPage'),
);
const GrindersPage = lazy(
  () => import('@/features/equipment/pages/GrindersPage'),
);
const BrewersPage = lazy(
  () => import('@/features/equipment/pages/BrewersPage'),
);
const PapersPage = lazy(() => import('@/features/equipment/pages/PapersPage'));
const WatersPage = lazy(() => import('@/features/equipment/pages/WatersPage'));
const BrewSetupsPage = lazy(
  () => import('@/features/brew-setups/BrewSetupsPage'),
);
const CuppingsListPage = lazy(
  () => import('@/features/cuppings/pages/CuppingsListPage'),
);
const CuppingDetailPage = lazy(
  () => import('@/features/cuppings/pages/CuppingDetailPage'),
);
const RatingDetailPage = lazy(
  () => import('@/features/ratings/RatingDetailPage'),
);
const PeoplePage = lazy(() => import('@/features/people/PeoplePage'));
const LookupsPage = lazy(() => import('@/features/settings/LookupsPage'));
const CampaignListPage = lazy(
  () => import('@/features/optimize/pages/CampaignListPage'),
);
const CampaignDetailPage = lazy(
  () => import('@/features/optimize/pages/CampaignDetailPage'),
);
const PersonPreferencesPage = lazy(
  () => import('@/features/people/pages/PersonPreferencesPage'),
);

const Loading = () => (
  <Box
    display="flex"
    justifyContent="center"
    alignItems="center"
    minHeight="60vh"
  >
    <CircularProgress />
  </Box>
);

function NotFoundPage() {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        gap: 2,
      }}
    >
      <Typography variant="h3">404</Typography>
      <Typography color="text.secondary">Page not found</Typography>
      <Button component={Link} to="/" variant="contained">
        Go to Dashboard
      </Button>
    </Box>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="beans" element={<BeansListPage />} />
          <Route path="beans/:beanId" element={<BeanDetailPage />} />
          <Route path="brews" element={<BrewsListPage />} />
          <Route path="brews/new" element={<BrewWizard />} />
          <Route path="brews/:brewId" element={<BrewDetailPage />} />
          <Route path="equipment/grinders" element={<GrindersPage />} />
          <Route path="equipment/brewers" element={<BrewersPage />} />
          <Route path="equipment/papers" element={<PapersPage />} />
          <Route path="equipment/waters" element={<WatersPage />} />
          <Route path="brew-setups" element={<BrewSetupsPage />} />
          <Route path="cuppings" element={<CuppingsListPage />} />
          <Route path="cuppings/:cuppingId" element={<CuppingDetailPage />} />
          <Route path="bean-ratings/:ratingId" element={<RatingDetailPage />} />
          <Route path="people" element={<PeoplePage />} />
          <Route path="settings/lookups" element={<LookupsPage />} />
          <Route path="/optimize" element={<CampaignListPage />} />
          <Route
            path="/optimize/:campaignId"
            element={<CampaignDetailPage />}
          />
          <Route
            path="/people/:personId/preferences"
            element={<PersonPreferencesPage />}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
