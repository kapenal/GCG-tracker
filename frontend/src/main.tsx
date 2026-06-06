import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import App from './App';
import './index.css';
import { queryClient } from './queryClient';
import { registerSW } from 'virtual:pwa-register';

registerSW({ immediate: true });

const persister = createSyncStoragePersister({
  storage: window.localStorage,
  key: 'gcg-query-cache',
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: 1000 * 60 * 30,
        dehydrateOptions: {
          shouldDehydrateQuery: (query) => {
            const root = query.queryKey[0];
            return root === 'sets' || root === 'rarities' || root === 'cards';
          },
        },
      }}
    >
      <App />
    </PersistQueryClientProvider>
  </StrictMode>
);
