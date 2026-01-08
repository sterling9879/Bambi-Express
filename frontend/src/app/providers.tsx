'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useState } from 'react';
import toast from 'react-hot-toast';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: (failureCount, error) => {
              // Não tentar novamente em erros 4xx (exceto 429)
              if (error instanceof Error) {
                const message = error.message.toLowerCase();
                if (message.includes('401') || message.includes('403') || message.includes('404')) {
                  return false;
                }
              }
              // Máximo 2 tentativas para outros erros
              return failureCount < 2;
            },
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
            // Não manter em cache queries que falharam
            gcTime: 5 * 60 * 1000,
            // Não refetch automaticamente quando falhar
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: false,
            onError: (error) => {
              const message = error instanceof Error ? error.message : 'Erro desconhecido';
              toast.error(message);
            },
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
            duration: 6000,
          },
        }}
      />
    </QueryClientProvider>
  );
}
