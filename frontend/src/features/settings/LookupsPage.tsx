import PageHeader from '@/components/PageHeader';
import { Box, Tab, Tabs } from '@mui/material';
import { useState } from 'react';
import LookupTab from './LookupTab';
import {
  beanVarietyHooks,
  brewMethodHooks,
  flavorTagHooks,
  originHooks,
  processMethodHooks,
  roasterHooks,
  stopModeHooks,
  storageTypeHooks,
  vendorHooks,
} from './hooks';

const tabs = [
  {
    label: 'Flavor Tags',
    entityName: 'Flavor Tag',
    hooks: flavorTagHooks,
    columns: [{ field: 'name', headerName: 'Name', flex: 1 }],
    fields: [{ name: 'name', label: 'Name', required: true }],
  },
  {
    label: 'Origins',
    entityName: 'Origin',
    hooks: originHooks,
    columns: [
      { field: 'name', headerName: 'Name', flex: 1 },
      { field: 'country', headerName: 'Country', flex: 1 },
      { field: 'region', headerName: 'Region', flex: 1 },
    ],
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'country', label: 'Country' },
      { name: 'region', label: 'Region' },
    ],
  },
  {
    label: 'Roasters',
    entityName: 'Roaster',
    hooks: roasterHooks,
    columns: [{ field: 'name', headerName: 'Name', flex: 1 }],
    fields: [{ name: 'name', label: 'Name', required: true }],
  },
  {
    label: 'Process Methods',
    entityName: 'Process Method',
    hooks: processMethodHooks,
    columns: [
      { field: 'name', headerName: 'Name', flex: 1 },
      { field: 'category', headerName: 'Category', width: 150 },
    ],
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'category', label: 'Category' },
    ],
  },
  {
    label: 'Bean Varieties',
    entityName: 'Bean Variety',
    hooks: beanVarietyHooks,
    columns: [
      { field: 'name', headerName: 'Name', flex: 1 },
      { field: 'species', headerName: 'Species', width: 150 },
    ],
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'species', label: 'Species' },
    ],
  },
  {
    label: 'Brew Methods',
    entityName: 'Brew Method',
    hooks: brewMethodHooks,
    columns: [{ field: 'name', headerName: 'Name', flex: 1 }],
    fields: [{ name: 'name', label: 'Name', required: true }],
  },
  {
    label: 'Stop Modes',
    entityName: 'Stop Mode',
    hooks: stopModeHooks,
    columns: [{ field: 'name', headerName: 'Name', flex: 1 }],
    fields: [{ name: 'name', label: 'Name', required: true }],
  },
  {
    label: 'Vendors',
    entityName: 'Vendor',
    hooks: vendorHooks,
    columns: [
      { field: 'name', headerName: 'Name', flex: 1 },
      { field: 'url', headerName: 'URL', flex: 1 },
      { field: 'location', headerName: 'Location', flex: 1 },
    ],
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'url', label: 'URL' },
      { name: 'location', label: 'Location' },
      { name: 'notes', label: 'Notes' },
    ],
  },
  {
    label: 'Storage Types',
    entityName: 'Storage Type',
    hooks: storageTypeHooks,
    columns: [{ field: 'name', headerName: 'Name', flex: 1 }],
    fields: [{ name: 'name', label: 'Name', required: true }],
  },
];

export default function LookupsPage() {
  const [activeTab, setActiveTab] = useState(0);
  return (
    <>
      <PageHeader title="Lookups" />
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs
          value={activeTab}
          onChange={(_, v) => setActiveTab(v)}
          variant="scrollable"
          scrollButtons="auto"
        >
          {tabs.map((t) => (
            <Tab key={t.label} label={t.label} />
          ))}
        </Tabs>
      </Box>
      {tabs.map((t, i) =>
        activeTab === i ? (
          <LookupTab
            key={t.label}
            hooks={t.hooks}
            columns={t.columns}
            fields={t.fields}
            entityName={t.entityName}
          />
        ) : null,
      )}
    </>
  );
}
