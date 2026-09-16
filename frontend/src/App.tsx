import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Route, Switch, Router as WouterRouter, useLocation } from 'wouter';
import { AppProvider, useAppContext } from '@/lib/app-context';
import { Navbar } from '@/components/navbar';
import { Toaster as SonnerToaster } from 'sonner';

import Login from '@/pages/login';
import Dashboard from '@/pages/panel';
import Icerikler from '@/pages/icerikler';
import KrizMerkezi from '@/pages/krizler';
import PRDanismani from '@/pages/pr-danismani';
import Ayarlar from '@/pages/ayarlar';

const queryClient = new QueryClient();

function ProtectedRoute({ component: Component }: { component: React.ComponentType }) {
  const { kullanici } = useAppContext();
  const [, setLocation] = useLocation();

  useEffect(() => {
    if (!kullanici) {
      setLocation('/');
    }
  }, [kullanici, setLocation]);

  if (!kullanici) return null;

  return <Component />;
}

function MainLayout({ children }: { children: React.ReactNode }) {
  const { kullanici } = useAppContext();
  const [location] = useLocation();

  const isLoginPage = location === "/";

  return (
    <div className="min-h-screen flex flex-col bg-background font-sans text-foreground selection:bg-primary/20 selection:text-primary">
      {!isLoginPage && <Navbar />}
      <main className={`flex-1 ${!isLoginPage ? 'max-w-7xl w-full mx-auto px-4 sm:px-6 py-8' : ''}`}>
        {children}
      </main>
      {!isLoginPage && (
        <footer className="mt-auto border-t border-border/70 bg-card/60 backdrop-blur-sm py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-center gap-2 text-center">
            <span className="w-1.5 h-1.5 rounded-full bg-signal/70" />
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest">
              Akademik araştırma sistemi — tüm skorlar backend'in açıklanabilir bilimsel modelleriyle (RepTrak, SCCT, EWMA) gerçek zamanlı hesaplanır.
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}

function Router() {
  return (
    <MainLayout>
      <Switch>
        <Route path="/" component={Login} />
        <Route path="/panel">
          {() => <ProtectedRoute component={Dashboard} />}
        </Route>
        <Route path="/icerikler">
          {() => <ProtectedRoute component={Icerikler} />}
        </Route>
        <Route path="/krizler">
          {() => <ProtectedRoute component={KrizMerkezi} />}
        </Route>
        <Route path="/pr-danismani">
          {() => <ProtectedRoute component={PRDanismani} />}
        </Route>
        <Route path="/ayarlar">
          {() => <ProtectedRoute component={Ayarlar} />}
        </Route>
        <Route>
          {() => (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
              <span className="text-xs font-bold uppercase tracking-[0.25em] text-signal mb-3">Sinyal bulunamadı</span>
              <h1 className="text-5xl font-bold font-display mb-2 grad-text">404</h1>
              <p className="text-muted-foreground">Aradığınız sayfa bulunamadı.</p>
            </div>
          )}
        </Route>
      </Switch>
    </MainLayout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <AppProvider>
            <Router />
            <SonnerToaster position="top-right" richColors />
          </AppProvider>
        </WouterRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
