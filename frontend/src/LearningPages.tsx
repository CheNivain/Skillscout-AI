import { useEffect, useState } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCheck,
  Clock3,
  ExternalLink,
  GitBranch,
  ListFilter,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  TrendingUp,
} from 'lucide-react';
import { api, date } from './api';
import {
  CourseCard,
  Empty,
  PageHeading,
  PanelHeading,
  Provider,
  RunButton,
  Spinner,
  Tags,
} from './components';
import type { Course, Post, Run, Saved, System, Trend } from './types';
import { useWorkspace } from './workspace';

export function ExplorePage({ initialSearch }: { initialSearch: string }) {
  const { dashboard } = useWorkspace();
  const [query, setQuery] = useState(initialSearch);
  const [category, setCategory] = useState('');
  const [level, setLevel] = useState('');
  const [kind, setKind] = useState('');
  const [free, setFree] = useState(false);
  const [sort, setSort] = useState('recommended');
  const [courses, setCourses] = useState<Course[]>([]);
  const [all, setAll] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setQuery(initialSearch);
  }, [initialSearch]);
  useEffect(() => {
    void api<Course[]>('/courses')
      .then(setAll)
      .catch(() => undefined);
  }, []);
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      if (query.trim()) params.set('q', query.trim());
      if (category) params.set('category', category);
      if (level) params.set('level', level);
      if (kind) params.set('kind', kind);
      if (free) params.set('free_only', 'true');
      void api<Course[]>(`/courses?${params}`)
        .then((data) => {
          if (!cancelled) setCourses(data);
        })
        .catch((e) => {
          if (!cancelled) setError(e.message);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, category, level, kind, free, retry]);
  const recs = new Map(dashboard.recommendations.map((rec) => [rec.course.id, rec]));
  const ordered = [...courses].sort((a, b) =>
    sort === 'price'
      ? a.price - b.price
      : sort === 'duration'
        ? a.duration_hours - b.duration_hours
        : sort === 'rating'
          ? b.rating - a.rating
          : query
            ? 0
            : (recs.get(b.id)?.score || 0) - (recs.get(a.id)?.score || 0),
  );
  const reset = () => {
    setQuery('');
    setCategory('');
    setLevel('');
    setKind('');
    setFree(false);
  };
  return (
    <>
      <PageHeading
        eyebrow="A WORLD OF POSSIBILITY"
        title="Course catalogue"
        description="Search courses, certifications and learning paths."
        action={<RunButton compact />}
      />
      <div className="catalogue-toolbar card">
        <div className="catalogue-search">
          <Search size={19} />
          <input
            aria-label="Search catalogue"
            placeholder="Try Python, cloud architecture, or a career goal…"
            value={query}
            maxLength={200}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="filter-row">
          <SlidersHorizontal size={17} />
          <select
            aria-label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {[...new Set(all.map((c) => c.category))].sort().map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select
            aria-label="Experience level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            <option value="">All levels</option>
            {['Beginner', 'Intermediate', 'Advanced'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            aria-label="Opportunity type"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="">All types</option>
            {['Course', 'Certification', 'Learning path'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <label className="checkbox-label">
            <input type="checkbox" checked={free} onChange={(e) => setFree(e.target.checked)} />
            Free opportunities
          </label>
          {(query || category || level || kind || free) && (
            <button className="text-button" onClick={reset}>
              Clear filters
            </button>
          )}
        </div>
      </div>
      <div className="results-heading">
        <p>
          <strong>{courses.length}</strong> opportunities {query && <>for “{query}”</>}
          <span> · Demo catalogue with provider links</span>
        </p>
        <label className="sort-control">
          <ListFilter size={16} />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            aria-label="Sort opportunities"
          >
            <option value="recommended">{query ? 'Search relevance' : 'Recommended first'}</option>
            <option value="price">Price: low to high</option>
            <option value="duration">Time: shortest first</option>
            <option value="rating">Highest rated</option>
          </select>
        </label>
      </div>
      {loading ? (
        <Spinner label="Searching learning opportunities…" />
      ) : error ? (
        <Empty
          title="The catalogue needs a moment."
          text={error}
          action={
            <button className="button secondary" onClick={() => setRetry(retry + 1)}>
              Try again
            </button>
          }
        />
      ) : ordered.length ? (
        <div className="catalogue-grid">
          {ordered.map((course) => (
            <CourseCard key={course.id} course={course} rec={recs.get(course.id)} />
          ))}
        </div>
      ) : (
        <Empty
          icon={<Search />}
          title="A different search might open a door."
          text="No opportunities match these filters. Try a broader skill or remove a filter."
          action={
            <button className="button secondary" onClick={reset}>
              Reset filters
            </button>
          }
        />
      )}
      <div className="info-box catalogue-note">
        <ShieldCheck size={18} />
        <p>
          Sample prices and offers support the assignment demonstration. Provider links are supplied
          for verification. SkillScout never enrolls you or makes purchases.
        </p>
      </div>
    </>
  );
}

export function PlanPage() {
  const { saved, save, remove, selectCourse, go } = useWorkspace();
  const [filter, setFilter] = useState<'all' | Saved['status']>('all');
  const completed = saved.filter((s) => s.status === 'completed').length;
  const hours = saved
    .filter((s) => s.status === 'in_progress')
    .reduce((sum, s) => sum + s.course.duration_hours, 0);
  const visible = saved.filter((s) => filter === 'all' || s.status === filter);
  return (
    <>
      <PageHeading
        eyebrow="SMALL STEPS, REAL PROGRESS"
        title="Learning plan"
        description="Manage saved courses and track your progress."
        action={
          <button className="button primary" onClick={() => go('explore')}>
            Find something to learn <ArrowRight size={16} />
          </button>
        }
      />
      <div className="plan-summary">
        <div>
          <BookOpen />
          <strong>{saved.length}</strong>
          <span>opportunities saved</span>
        </div>
        <div>
          <Clock3 />
          <strong>{hours}</strong>
          <span>hours in progress</span>
        </div>
        <div>
          <CheckCheck />
          <strong>{completed}</strong>
          <span>courses completed</span>
        </div>
        <div className="completion-summary">
          <span>
            {saved.length ? Math.round((completed / saved.length) * 100) : 0}% of your plan complete
          </span>
          <div className="progress-track">
            <i style={{ width: `${saved.length ? (completed / saved.length) * 100 : 0}%` }} />
          </div>
        </div>
      </div>
      <div className="tab-row" role="group" aria-label="Plan status">
        {(['all', 'saved', 'in_progress', 'completed'] as const).map((status) => (
          <button
            className={filter === status ? 'active' : ''}
            key={status}
            onClick={() => setFilter(status)}
          >
            {status === 'all'
              ? 'All learning'
              : status === 'in_progress'
                ? 'In progress'
                : status === 'saved'
                  ? 'Saved for later'
                  : 'Completed'}
            <span>
              {status === 'all' ? saved.length : saved.filter((s) => s.status === status).length}
            </span>
          </button>
        ))}
      </div>
      {visible.length ? (
        <div className="plan-list">
          {visible.map((item) => (
            <article key={item.course.id} className={`plan-item card ${item.status}`}>
              <Provider provider={item.course.provider} large />
              <div className="plan-item-main">
                <span className={`pill status-${item.status}`}>
                  {item.status.replace('_', ' ')}
                </span>
                <button className="course-title" onClick={() => selectCourse(item.course)}>
                  {item.course.title}
                </button>
                <p className="muted small">
                  {item.course.provider} · {item.course.duration_hours} hours · Saved{' '}
                  {date(item.saved_at)}
                  {item.completed_at ? ` · Completed ${date(item.completed_at)}` : ''}
                </p>
                <Tags values={item.course.skills} limit={4} />
              </div>
              <div className="plan-item-actions">
                <select
                  aria-label={`Learning status for ${item.course.title}`}
                  value={item.status}
                  onChange={(e) => void save(item.course, e.target.value as Saved['status'])}
                >
                  <option value="saved">Saved for later</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                </select>
                <a
                  className="text-button"
                  href={item.course.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open course <ExternalLink size={14} />
                </a>
                <button
                  className="icon-button danger-text"
                  aria-label={`Remove ${item.course.title} from plan`}
                  title="Remove from plan"
                  onClick={() => void remove(item.course)}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="card">
          <Empty
            icon={<BookOpen size={28} />}
            title={
              filter === 'all' ? 'Make space for your next chapter.' : 'Nothing in this stage yet.'
            }
            text={
              filter === 'all'
                ? 'Save opportunities from the catalogue or your recommendations. Then track your progress at your own pace.'
                : 'Change a course’s learning status to see it here.'
            }
            action={
              <button className="button primary" onClick={() => go('explore')}>
                Courses <ArrowRight size={15} />
              </button>
            }
          />
        </div>
      )}
      <p className="data-caption">
        Progress is self-reported. Marking a course complete adds its skills to your profile; run
        your agents again for a fresh plan.
      </p>
    </>
  );
}

export function TrendsPage() {
  const { dashboard } = useWorkspace();
  const [data, setData] = useState<{ trends: Trend[]; posts: Post[]; corpus_note: string } | null>(
    null,
  );
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('');
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let alive = true;
    void api<{ trends: Trend[]; posts: Post[]; corpus_note: string }>('/trends')
      .then((v) => {
        if (alive) {
          setData(v);
          setError('');
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [dashboard.last_run?.id, reload]);
  const focus = data?.trends.find((t) => t.skill === selected) || data?.trends[0];
  return (
    <>
      <PageHeading
        eyebrow="KEEP YOUR CURIOSITY CURRENT"
        title="Learning trends"
        description="Skills and certifications surfaced from the professional learning corpus."
        action={<RunButton compact />}
      />
      <div className="notice warm">
        <TrendingUp size={19} />
        <p>
          {data?.corpus_note ||
            'Trends reflect a synthetic demonstration corpus, not real-time LinkedIn activity or market demand.'}
        </p>
      </div>
      {error ? (
        <Empty
          title="Couldn’t load learning signals."
          text={error}
          action={
            <button className="button secondary" onClick={() => setReload(reload + 1)}>
              Retry
            </button>
          }
        />
      ) : !data ? (
        <Spinner />
      ) : data.trends.length ? (
        <div className="trends-layout">
          <section className="card trend-list-panel">
            <PanelHeading
              title="Signals worth exploring"
              sub={`${data.trends.length} skills discovered`}
            />
            {data.trends.map((trend, index) => (
              <button
                className={`trend-select ${focus?.skill === trend.skill ? 'active' : ''}`}
                key={trend.skill}
                onClick={() => setSelected(trend.skill)}
              >
                <span className="trend-number">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <strong>{trend.skill}</strong>
                  <small>{trend.mentions} mentions in the corpus</small>
                  <div className="progress-track">
                    <i style={{ width: `${Math.max(0, Math.min(100, trend.score))}%` }} />
                  </div>
                </div>
                <span className={trend.growth_percent > 0 ? 'trend-growth' : 'muted'}>
                  {trend.growth_percent > 0 ? '+' : ''}
                  {Math.round(trend.growth_percent)}%
                </span>
              </button>
            ))}
            <p className="data-caption">
              Growth compares recent and earlier corpus windows. Small samples can produce large
              percentages.
            </p>
          </section>
          <section className="card trend-detail">
            {focus && (
              <>
                <p className="eyebrow">FOLLOW THE EVIDENCE</p>
                <h2>{focus.skill}</h2>
                <p className="muted">{focus.summary}</p>
                <Tags values={focus.related_skills} limit={12} />
                <div className="trend-metrics">
                  <div>
                    <strong>{focus.mentions}</strong>
                    <span>learning mentions</span>
                  </div>
                  <div>
                    <strong>
                      {Math.round(focus.score)}
                      <small>/100</small>
                    </strong>
                    <span>signal score</span>
                  </div>
                  <div>
                    <strong>
                      {focus.growth_percent > 0 ? '+' : ''}
                      {Math.round(focus.growth_percent)}%
                    </strong>
                    <span>corpus-window change</span>
                  </div>
                </div>
                <h3>Where this signal comes from</h3>
                <div className="evidence-list">
                  {focus.evidence.map((post) => (
                    <article className="evidence" key={post.id}>
                      <div>
                        <span className="source-avatar">{post.source.slice(0, 1)}</span>
                        <div>
                          <strong>{post.source}</strong>
                          <small>
                            {date(post.published_at)}
                            {post.is_demo ? ' · Synthetic sample' : ' · Imported content'}
                          </small>
                        </div>
                        {post.source_url && (
                          <a
                            className="icon-button"
                            href={post.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`View ${post.source} source`}
                          >
                            <ArrowUpRight size={16} />
                          </a>
                        )}
                      </div>
                      <p>{post.text}</p>
                    </article>
                  ))}
                </div>
              </>
            )}
          </section>
        </div>
      ) : (
        <div className="card">
          <Empty
            icon={<TrendingUp size={28} />}
            title="Your learning radar is ready."
            text={`${data.posts.length} learning posts are available. Run your agents to extract skill mentions and discover relevant signals.`}
            action={<RunButton />}
          />
        </div>
      )}
    </>
  );
}

export function AgentsPage() {
  const { activeRun, running, dashboard } = useWorkspace();
  const [system, setSystem] = useState<System | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [pickedRun, setPickedRun] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function load() {
    setLoading(true);
    try {
      const [s, r] = await Promise.all([api<System>('/system'), api<Run[]>('/runs')]);
      setSystem(s);
      setRuns(r);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [dashboard.last_run?.id, running]);
  const selected = pickedRun ? runs.find((r) => r.id === pickedRun) : activeRun || runs[0];
  const descriptions = [
    'Understand your current skills, role and career direction.',
    'Extract skills and topics from professional learning content.',
    'Retrieve actual courses with relevance-ranked information retrieval.',
    'Weigh fit, time, cost and trends, then explain each opportunity.',
  ];
  return (
    <>
      <PageHeading
        eyebrow="FOUR AGENTS. ONE SHARED DIRECTION."
        title="Agent activity"
        description="A transparent view of the HTTP workflow behind every recommendation."
        action={<RunButton compact />}
      />
      <div className="agent-grid">
        {[
          'Profile & training needs',
          'Learning trend discovery',
          'Training opportunity retrieval',
          'Recommendation & notification',
        ].map((name, i) => {
          const agent = system?.agents[i];
          const step = !pickedRun && running ? activeRun?.steps[i] : undefined;
          return (
            <section
              className={`card agent-card ${step?.status === 'running' ? 'agent-working' : ''}`}
              key={name}
            >
              <div className="agent-card-top">
                <span className={`agent-icon tone-${i}`}>
                  <GitBranch size={23} />
                </span>
                <span
                  className={`pill ${agent?.status === 'online' ? 'status-completed' : 'status-saved'}`}
                >
                  <span className={`status-dot ${agent?.status === 'online' ? '' : 'amber'}`} />
                  {step?.status === 'running' ? 'Working' : agent?.status || 'Checking'}
                </span>
              </div>
              <p className="eyebrow">AGENT 0{i + 1}</p>
              <h3>{name}</h3>
              <p className="muted">{descriptions[i]}</p>
              <div className="agent-endpoint">
                <span>HTTP / REST</span>
                <code>:{agent?.port || 8101 + i} /execute</code>
              </div>
            </section>
          );
        })}
      </div>
      <div className="agent-mode card">
        <div>
          <Sparkles size={22} />
          <div>
            <h3>
              {system?.mode.llm_available
                ? `Local intelligence · ${system.mode.model}`
                : 'Rules-based fallback is available'}
            </h3>
            <p>{system?.mode.description || dashboard.mode.description}</p>
          </div>
        </div>
        <button className="button secondary" disabled={loading} onClick={() => void load()}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          Check services
        </button>
      </div>
      {error && <div className="notice error">{error}</div>}
      <div className="agent-lower-grid">
        <section className="card trace-panel">
          <PanelHeading
            title="Run details"
            sub="Real execution records, with the inputs and outputs at each step."
            action={
              <span className={`pill status-${selected?.status || 'saved'}`}>
                {selected?.status || 'Ready to run'}
              </span>
            }
          />
          {selected ? (
            <>
              <div className="trace-run-meta">
                <span>{new Date(selected.started_at).toLocaleString()}</span>
                <code>{selected.id.slice(0, 12)}</code>
              </div>
              {selected.error && <div className="form-error">{selected.error}</div>}
              <div className="trace-list">
                {selected.steps.map((step, i) => (
                  <div className={`trace-step ${step.status}`} key={step.agent}>
                    <span className="trace-number">
                      {step.status === 'completed' ? <CheckCheck size={17} /> : `0${i + 1}`}
                    </span>
                    <div className="trace-content">
                      <div className="trace-title">
                        <h3>{step.label}</h3>
                        <span>
                          {step.status}
                          {step.duration_ms > 0
                            ? ` · ${(step.duration_ms / 1000).toFixed(2)}s`
                            : ''}
                        </span>
                      </div>
                      {step.error && <p className="form-error">{step.error}</p>}
                      <details>
                        <summary>Inspect agent payload</summary>
                        <div className="payload-grid">
                          <div>
                            <p>INPUT</p>
                            <pre>{JSON.stringify(step.input, null, 2)}</pre>
                          </div>
                          <div>
                            <p>OUTPUT</p>
                            <pre>{JSON.stringify(step.output, null, 2)}</pre>
                          </div>
                        </div>
                      </details>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <Empty
              icon={<GitBranch />}
              title="A clear path from profile to opportunity."
              text="Start a discovery run to inspect the four agents’ actual REST handoffs and results."
              action={<RunButton />}
            />
          )}
        </section>
        <aside>
          <section className="card history-panel">
            <PanelHeading title="Recent runs" />
            {runs.length ? (
              <div className="run-history">
                {runs.map((run) => (
                  <button
                    className={selected?.id === run.id ? 'active' : ''}
                    key={run.id}
                    onClick={() => setPickedRun(run.id)}
                  >
                    <span className={`status-dot ${run.status === 'completed' ? '' : 'amber'}`} />
                    <div>
                      <strong>
                        {new Date(run.started_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </strong>
                      <small>
                        {run.status} · {run.steps.filter((s) => s.status === 'completed').length}/4
                        agents
                      </small>
                    </div>
                    <ArrowRight size={15} />
                  </button>
                ))}
              </div>
            ) : (
              <p className="muted small">
                Your completed and failed discovery runs will appear here.
              </p>
            )}
            {pickedRun && (
              <button className="text-button" onClick={() => setPickedRun(null)}>
                Back to latest run
              </button>
            )}
          </section>
          <section className="card scheduler-panel">
            <ShieldCheck size={23} />
            <h3>Scheduled discovery</h3>
            <p className="muted">
              {system?.scheduler.enabled
                ? `The scheduler checks every ${system.scheduler.interval_minutes} minutes for employees who enabled analysis and notifications.`
                : 'Scheduled discovery is disabled. You can run the agents at any time.'}
            </p>
            <p className="small muted">
              {system?.scheduler.last_checked_at
                ? `Last check: ${new Date(system.scheduler.last_checked_at).toLocaleString()}`
                : 'No scheduled check recorded.'}
            </p>
            <div className="mini-facts">
              <span>{system?.catalogue_count ?? '—'} catalogue entries</span>
              <span>{system?.post_count ?? '—'} learning posts</span>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
