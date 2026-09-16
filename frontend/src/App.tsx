import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Bell,
  BookOpen,
  Building2,
  ChevronDown,
  Compass,
  GitBranch,
  LayoutDashboard,
  Leaf,
  LogOut,
  Menu,
  MessageCircle,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react';
import Auth from './Auth';
import DashboardPage from './Dashboard';
import { AgentsPage, ExplorePage, PlanPage, TrendsPage } from './LearningPages';
import { SettingsPage, OrganizationPage } from './SettingsPages';
import { ChatPanel, NotificationsPanel } from './Panels';
import { Brand, CourseDetail, Spinner } from './components';
import { api, initials, setCsrf } from './api';
import { WorkspaceContext } from './workspace';
import type { Page } from './workspace';
import type { Course, Dashboard, Recommendation, Run, Saved, User } from './types';

const nav = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'explore', label: 'Courses', icon: Compass },
  { id: 'plan', label: 'Learning plan', icon: BookOpen },
  { id: 'trends', label: 'Learning trends', icon: TrendingUp },
  { id: 'agents', label: 'Agent activity', icon: GitBranch },
] as const;
const pageNames: Record<Page, string> = {
  overview: 'Overview',
  explore: 'Courses',
  plan: 'Learning plan',
  trends: 'Learning trends',
  agents: 'Agent activity',
  settings: 'Profile & settings',
  organization: 'Organization',
};
const currentPage = (): Page => {
  const key = window.location.hash.slice(1);
  return Object.hasOwn(pageNames, key) ? (key as Page) : 'overview';
};

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [authError, setAuthError] = useState('');
  const loadSession = useCallback(async () => {
    setInitializing(true);
    setAuthError('');
    try {
      const result = await api<{ user: User; csrf_token: string }>('/auth/session');
      setCsrf(result.csrf_token);
      setUser(result.user);
    } catch (e) {
      if (!(e instanceof Error && 'status' in e && e.status === 401))
        setAuthError((e as Error).message);
    } finally {
      setInitializing(false);
    }
  }, []);
  useEffect(() => {
    void loadSession();
  }, [loadSession]);
  if (initializing)
    return (
      <div className="boot-screen">
        <Brand />
        <Spinner />
      </div>
    );
  if (authError)
    return (
      <div className="boot-screen">
        <Brand />
        <h2>Your workspace needs a connection.</h2>
        <p>{authError}</p>
        <p className="muted">
          Start SkillScout from VS Code with <code>python scripts/dev.py</code>, then try again.
        </p>
        <button className="button primary" onClick={() => void loadSession()}>
          Try again
        </button>
      </div>
    );
  return user ? (
    <Workspace
      key={user.id}
      user={user}
      onLogout={() => {
        setUser(null);
        setCsrf('');
      }}
    />
  ) : (
    <Auth onLogin={setUser} />
  );
}

function Workspace({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [page, setPage] = useState<Page>(() =>
    window.location.hash ? currentPage() : user.role === 'employee' ? 'overview' : 'organization',
  );
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [selected, setSelected] = useState<{ course: Course; rec?: Recommendation } | null>(null);
  const [chat, setChat] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; error: boolean } | null>(null);
  const [search, setSearch] = useState('');
  const [catalogueSearch, setCatalogueSearch] = useState('');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mutations = useRef(new Set<string>());
  const toast = useCallback((text: string, isError = false) => {
    setToastMessage({ text, error: isError });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMessage(null), 6000);
  }, []);
  const refresh = useCallback(async () => {
    try {
      const [d, s] = await Promise.all([
        api<Dashboard>('/dashboard'),
        api<Saved[]>('/learning-plan'),
      ]);
      setDashboard(d);
      setSaved(s);
      setActiveRun(d.last_run);
      setError('');
    } catch (e) {
      if (e instanceof Error && 'status' in e && e.status === 401) onLogout();
      else {
        setError((e as Error).message);
        throw e;
      }
    }
  }, [onLogout]);
  // The initial fetch belongs to this user's mounted workspace. Later mutations refresh explicitly.
  useEffect(() => {
    void refresh().catch(() => undefined);
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);
  const go = useCallback((next: Page) => {
    window.location.hash = next;
    setPage(next);
    setMobile(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);
  useEffect(() => {
    const listener = () => {
      setPage(currentPage());
      setMobile(false);
    };
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  useEffect(() => {
    if (!running) return;
    let stopped = false;
    const poll = async () => {
      try {
        const runs = await api<Run[]>('/runs');
        if (!stopped && runs[0]) setActiveRun(runs[0]);
      } catch {
        /* The final request reports transport errors. */
      }
    };
    const interval = setInterval(() => void poll(), 1200);
    void poll();
    return () => {
      stopped = true;
      clearInterval(interval);
    };
  }, [running]);
  async function run() {
    if (running) return;
    if (!dashboard?.profile.consent) {
      toast('Enable learning analysis in your profile to run your agents.', true);
      go('settings');
      return;
    }
    setRunning(true);
    try {
      const result = await api<Run>('/runs', 'POST');
      setActiveRun(result);
      await refresh();
      if (result.status === 'failed')
        toast(result.error || 'The agent run failed. Open Agent activity for details.', true);
      else toast('Recommendations updated.');
    } catch (e) {
      toast((e as Error).message, true);
    } finally {
      setRunning(false);
    }
  }
  async function save(course: Course, status: Saved['status'] = 'saved') {
    if (mutations.current.has(course.id)) return;
    mutations.current.add(course.id);
    try {
      await api(`/learning-plan/${encodeURIComponent(course.id)}`, 'PUT', { status });
      await refresh();
      toast(
        status === 'completed'
          ? 'Course marked complete.'
          : status === 'in_progress'
            ? 'Course marked in progress.'
            : 'Added to your learning plan.',
      );
    } catch (e) {
      toast((e as Error).message, true);
    } finally {
      mutations.current.delete(course.id);
    }
  }
  async function remove(course: Course) {
    try {
      await api(`/learning-plan/${encodeURIComponent(course.id)}`, 'DELETE');
      await refresh();
      toast('Removed from your learning plan.');
    } catch (e) {
      toast((e as Error).message, true);
    }
  }
  async function logout() {
    try {
      await api('/auth/logout', 'POST');
      onLogout();
    } catch (e) {
      toast((e as Error).message, true);
    }
  }
  if (!dashboard)
    return (
      <div className="boot-screen">
        <Brand />
        {error ? (
          <>
            <h2>We couldn’t open your workspace.</h2>
            <p className="form-error">{error}</p>
            <button
              className="button primary"
              onClick={() => void refresh().catch(() => undefined)}
            >
              Try again
            </button>
            <button className="text-button" onClick={() => void logout()}>
              Back to sign in
            </button>
          </>
        ) : (
          <Spinner />
        )}
      </div>
    );
  const safePage = page === 'organization' && user.role === 'employee' ? 'overview' : page;
  return (
    <WorkspaceContext.Provider
      value={{
        user,
        dashboard,
        saved,
        running,
        activeRun,
        go,
        refresh,
        run,
        selectCourse: (course, rec) => setSelected({ course, rec }),
        save,
        remove,
        toast,
        openChat: () => setChat(true),
      }}
    >
      <div className="app-shell">
        {mobile && (
          <button
            className="mobile-scrim"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          />
        )}
        <aside className={`sidebar ${mobile ? 'is-open' : ''}`}>
          <button
            className="brand-home"
            onClick={() => go('overview')}
            aria-label="SkillScout overview"
          >
            <Brand />
          </button>
          <div className="workspace-selector">
            <span className="workspace-icon">
              <Leaf size={18} />
            </span>
            <div>
              <strong>My workspace</strong>
              <small>
                {user.role === 'employee'
                  ? 'Personal learning'
                  : user.role === 'hr'
                    ? 'HR & development'
                    : 'Administrator'}
              </small>
            </div>
            <ChevronDown size={14} />
          </div>
          <p className="nav-label">DISCOVER YOUR POTENTIAL</p>
          <nav aria-label="Main navigation">
            {nav.map((item) => (
              <button
                key={item.id}
                className={`nav-item ${safePage === item.id ? 'active' : ''}`}
                aria-current={safePage === item.id ? 'page' : undefined}
                onClick={() => go(item.id)}
              >
                <item.icon size={19} />
                {item.label}
                {item.id === 'plan' && saved.length > 0 && (
                  <span className="nav-count">{saved.length}</span>
                )}
              </button>
            ))}
            {user.role !== 'employee' && (
              <button
                className={`nav-item ${safePage === 'organization' ? 'active' : ''}`}
                onClick={() => go('organization')}
              >
                <Building2 size={19} />
                Organization
              </button>
            )}
          </nav>
          <div className="sidebar-bottom">
            <div className="scout-invite">
              <span className="invite-star">✦</span>
              <h3>Learning assistant</h3>
              <p>Find a little clarity with your learning assistant.</p>
              <button onClick={() => setChat(true)}>
                Ask Scout <MessageCircle size={15} />
              </button>
            </div>
            <button
              className={`nav-item ${safePage === 'settings' ? 'active' : ''}`}
              onClick={() => go('settings')}
            >
              <Settings2 size={18} />
              Profile & settings
            </button>

            <div className="sidebar-user">
              <span className="avatar">{initials(user.name)}</span>
              <div>
                <strong>{user.name}</strong>
                <small>{user.role === 'hr' ? 'HR / L&D' : user.role}</small>
              </div>
              <button
                className="icon-button"
                aria-label="Sign out"
                title="Sign out"
                onClick={() => void logout()}
              >
                <LogOut size={17} />
              </button>
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu />
            </button>
            <div className="breadcrumb">
              My workspace <span>/</span>
              <strong>{pageNames[safePage]}</strong>
            </div>
            <form
              className="global-search"
              onSubmit={(e) => {
                e.preventDefault();
                setCatalogueSearch(search.trim());
                go('explore');
              }}
            >
              <Search size={16} />
              <input
                aria-label="Search learning opportunities"
                placeholder="Find your next opportunity…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <kbd>↵</kbd>
            </form>
            <div className="topbar-actions">
              <button
                className="icon-button notification-button"
                aria-label={`Notifications, ${dashboard.stats.unread_notifications} unread`}
                onClick={() => setNotifications(true)}
              >
                <Bell size={20} />
                {dashboard.stats.unread_notifications > 0 && <span className="notification-dot" />}
              </button>
              <span className="topbar-divider" />
              <button className="avatar" aria-label="Open profile" onClick={() => go('settings')}>
                {initials(user.name)}
              </button>
            </div>
          </header>
          <main id="main-content" className="main-content">
            {error && (
              <div className="notice error">
                {error}
                <button
                  className="text-button"
                  onClick={() => void refresh().catch(() => undefined)}
                >
                  Retry
                </button>
              </div>
            )}
            {safePage === 'overview' && <DashboardPage />}
            {safePage === 'explore' && <ExplorePage initialSearch={catalogueSearch} />}{' '}
            {safePage === 'plan' && <PlanPage />}
            {safePage === 'trends' && <TrendsPage />}
            {safePage === 'agents' && <AgentsPage />}
            {safePage === 'settings' && <SettingsPage onDeleted={onLogout} />}{' '}
            {safePage === 'organization' && <OrganizationPage />}
          </main>
          <footer className="app-footer">
            <span>
              <ShieldCheck size={13} /> Your learning. Your choices.
            </span>
            <button onClick={() => go('agents')}>
              <span className={`status-dot ${dashboard.mode.llm_available ? '' : 'amber'}`} />
              {dashboard.mode.llm_available
                ? `Local AI · ${dashboard.mode.model}`
                : 'Rules-based mode · Ollama unavailable'}
            </button>
            <span>SkillScout AI · Local workspace</span>
          </footer>
        </div>
      </div>
      {running && (
        <button className="run-progress" onClick={() => go('agents')}>
          <Sparkles size={17} className="pulse" />
          <span>
            <strong>Your agents are at work</strong>
            <small>
              {activeRun?.steps.find((s) => s.status === 'running')?.label ||
                'Preparing your learning recommendations…'}
            </small>
          </span>
          <GitBranch size={18} />
        </button>
      )}
      {selected && <CourseDetail {...selected} onClose={() => setSelected(null)} />}{' '}
      {chat && <ChatPanel onClose={() => setChat(false)} />}{' '}
      {notifications && <NotificationsPanel onClose={() => setNotifications(false)} />}
      {toastMessage && (
        <div
          role={toastMessage.error ? 'alert' : 'status'}
          className={`toast ${toastMessage.error ? 'toast-error' : ''}`}
        >
          <span>{toastMessage.text}</span>
          <button aria-label="Dismiss notification" onClick={() => setToastMessage(null)}>
            <X size={17} />
          </button>
        </div>
      )}
    </WorkspaceContext.Provider>
  );
}
