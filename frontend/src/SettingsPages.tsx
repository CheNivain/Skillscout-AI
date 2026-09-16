import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import {
  BookOpen,
  Building2,
  CheckCheck,
  Download,
  FilePlus2,
  LockKeyhole,
  Plus,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
} from 'lucide-react';
import { api, initials } from './api';
import { Drawer, Empty, PageHeading, PanelHeading, Spinner } from './components';
import type { Overview, Profile } from './types';
import { useWorkspace } from './workspace';

const splitLines = (value: string) => [
  ...new Set(
    value
      .split('\n')
      .map((v) => v.trim())
      .filter(Boolean),
  ),
];
const split = (value: string) => [
  ...new Set(
    value
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean),
  ),
];

export function SettingsPage({ onDeleted }: { onDeleted: () => void }) {
  const { user, dashboard, refresh, toast } = useWorkspace();
  const [profile, setProfile] = useState<Profile>({ ...dashboard.profile });
  const [skills, setSkills] = useState(profile.skills.join(', '));
  const [certs, setCerts] = useState(profile.certifications.join('\n'));
  const [history, setHistory] = useState(profile.training_history.join('\n'));
  const [interests, setInterests] = useState(profile.interests.join(', '));
  const [busy, setBusy] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const update = <K extends keyof Profile>(key: K, value: Profile[K]) =>
    setProfile((p) => ({ ...p, [key]: value }));
  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const next = {
        ...profile,
        skills: split(skills),
        certifications: splitLines(certs),
        training_history: splitLines(history),
        interests: split(interests),
      };
      await api('/profile', 'PUT', next);
      await refresh();
      toast('Profile updated. Run your agents to discover opportunities for your new goals.');
    } catch (e) {
      toast((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  async function exportData() {
    try {
      const data = await api('/privacy/export');
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }),
      );
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `skillscout-data-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast('Your data export is ready.');
    } catch (e) {
      toast((e as Error).message, true);
    }
  }
  async function deleteAccount(event: FormEvent) {
    event.preventDefault();
    if (!confirmDelete) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await api('/privacy/account', 'DELETE', { password });
      onDeleted();
    } catch (e) {
      setDeleteError((e as Error).message);
      setDeleting(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="BUILT AROUND YOU"
        title="Profile & settings"
        description="Update your professional profile and preferences."
      />
      <div className="settings-layout">
        <form className="profile-form" onSubmit={(event) => void saveProfile(event)}>
          <section className="card settings-section">
            <div className="profile-identity">
              <span className="avatar large-avatar">{initials(user.name)}</span>
              <div>
                <h2>{user.name}</h2>
                <p>{user.email}</p>
              </div>
              <span className="pill status-saved">
                {user.role === 'hr' ? 'HR / L&D' : user.role}
              </span>
            </div>
            <PanelHeading
              title="Your professional story"
              sub="Only professional context is used for learning recommendations."
            />
            <div className="form-grid">
              <label>
                Current role
                <input
                  maxLength={120}
                  placeholder="e.g. Data Analyst"
                  value={profile.role_title}
                  onChange={(e) => update('role_title', e.target.value)}
                />
              </label>
              <label>
                Career goal
                <input
                  maxLength={160}
                  placeholder="e.g. Data Scientist"
                  value={profile.career_goal}
                  onChange={(e) => update('career_goal', e.target.value)}
                />
              </label>
              <label>
                Years of experience
                <input
                  type="number"
                  min={0}
                  max={60}
                  step="0.5"
                  required
                  value={profile.experience_years}
                  onChange={(e) => update('experience_years', Number(e.target.value))}
                />
              </label>
              <label>
                Weekly learning hours
                <input
                  type="number"
                  min={0.5}
                  max={60}
                  step="0.5"
                  required
                  value={profile.weekly_hours}
                  onChange={(e) => update('weekly_hours', Number(e.target.value))}
                />
              </label>
              <label className="full-width">
                Current skills
                <input
                  maxLength={5000}
                  value={skills}
                  onChange={(e) => setSkills(e.target.value)}
                  placeholder="SQL, Excel, Power BI"
                />
                <small>
                  Separate skills with commas. Completed courses also update your skills.
                </small>
              </label>
              <label className="full-width">
                Existing certifications
                <textarea
                  rows={2}
                  maxLength={10000}
                  value={certs}
                  onChange={(e) => setCerts(e.target.value)}
                  placeholder="One certification per line"
                />
              </label>
              <label className="full-width">
                Training history
                <textarea
                  maxLength={10000}
                  rows={3}
                  value={history}
                  onChange={(e) => setHistory(e.target.value)}
                  placeholder="One completed course or training activity per line; commas inside titles are preserved"
                />
              </label>
              <label>
                Learning interests
                <input
                  maxLength={5000}
                  value={interests}
                  onChange={(e) => setInterests(e.target.value)}
                  placeholder="Data visualization, AI"
                />
              </label>
              <label>
                Budget per opportunity (USD)
                <input
                  type="number"
                  min={0}
                  max={100000}
                  step="0.01"
                  required
                  value={profile.budget}
                  onChange={(e) => update('budget', Number(e.target.value))}
                />
              </label>
              <label className="full-width">
                Anything else about your goals?
                <textarea
                  rows={3}
                  maxLength={2000}
                  value={profile.bio}
                  onChange={(e) => update('bio', e.target.value)}
                  placeholder="What would you love to work on next?"
                />
                <small>Avoid including sensitive personal information.</small>
              </label>
            </div>
          </section>
          <section className="card settings-section">
            <PanelHeading
              title="Your data, your choice"
              sub="You control whether your professional profile is analyzed."
            />
            <label className="toggle-row">
              <div>
                <strong>Allow personalized learning analysis</strong>
                <p>
                  Let the four agents use your role, skills, goals and training history to find
                  relevant opportunities. Withdrawing consent clears current recommendations and
                  stops future analysis. Past run records remain private until account deletion.
                </p>
              </div>
              <input
                type="checkbox"
                role="switch"
                checked={profile.consent}
                onChange={(e) => update('consent', e.target.checked)}
              />
            </label>
            <label className="toggle-row">
              <div>
                <strong>Proactive opportunity notifications</strong>
                <p>
                  Receive in-app alerts and scheduled discoveries when relevant opportunities are
                  found. Analysis consent is also required.
                </p>
              </div>
              <input
                type="checkbox"
                role="switch"
                checked={profile.notifications_enabled}
                onChange={(e) => update('notifications_enabled', e.target.checked)}
              />
            </label>
            <div className="form-actions">
              <button className="button primary" disabled={busy}>
                <Save size={17} />
                {busy ? 'Saving your profile…' : 'Save profile & preferences'}
              </button>
            </div>
          </section>
        </form>
        <aside>
          <section className="card trust-card">
            <span className="trust-icon">
              <ShieldCheck size={25} />
            </span>
            <h2>Privacy</h2>
            <p>
              Your professional profile stays in this local workspace. With local Ollama, model
              requests are processed on your computer.
            </p>
            <ul>
              <li>
                <LockKeyhole size={16} /> Passwords are hashed; authenticated sessions protect your
                account.
              </li>
              <li>
                <Users size={16} /> HR sees aggregate learning insights. Administrators manage the
                catalogue.
              </li>
              <li>
                <Sparkles size={16} /> Recommendations explain their match and use retrieved course
                records.
              </li>
              <li>
                <CheckCheck size={16} /> You make every learning decision. No employment decisions
                are automated.
              </li>
            </ul>
          </section>
          <section className="card data-control">
            <PanelHeading title="Take your data with you" />
            <p className="muted small">
              Download your profile, learning plan and activity as a JSON file.
            </p>
            <button className="button secondary" onClick={() => void exportData()}>
              <Download size={16} />
              Export my data
            </button>
          </section>
          <section className="card data-control danger-zone">
            <PanelHeading title="Delete your account" />
            <p className="muted small">
              Permanently remove your profile, sessions and learning activity from this workspace.
            </p>
            <button className="text-button danger-text" onClick={() => setDeleteOpen(true)}>
              <Trash2 size={15} />
              Delete account
            </button>
          </section>
        </aside>
      </div>
      {deleteOpen && (
        <Drawer
          title="Delete your workspace account?"
          subtitle="PERMANENT DATA REMOVAL"
          onClose={() => {
            if (!deleting) setDeleteOpen(false);
          }}
        >
          <form className="drawer-content" onSubmit={(e) => void deleteAccount(e)}>
            <p>
              Your profile, recommendations, learning plan, notifications and sessions will be
              permanently deleted. The shared catalogue remains available to other users.
            </p>
            <label>
              Confirm your password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <label className="checkbox-label deletion-confirm">
              <input
                type="checkbox"
                checked={confirmDelete}
                onChange={(e) => setConfirmDelete(e.target.checked)}
              />
              I understand that deleting my account cannot be undone.
            </label>
            {deleteError && (
              <p className="form-error" role="alert">
                {deleteError}
              </p>
            )}
            <button className="button danger" disabled={!confirmDelete || deleting}>
              <Trash2 size={17} />
              {deleting ? 'Deleting…' : 'Permanently delete my account'}
            </button>
          </form>
        </Drawer>
      )}
    </>
  );
}

type CourseForm = {
  title: string;
  provider: string;
  url: string;
  description: string;
  skills: string;
  category: string;
  level: string;
  duration_hours: string;
  rating: string;
  price: string;
  original_price: string;
  offer_expires_at: string;
  kind: string;
  is_demo: boolean;
  source_note: string;
};
const blankCourse: CourseForm = {
  title: '',
  provider: '',
  url: '',
  description: '',
  skills: '',
  category: 'Data Science',
  level: 'Beginner',
  duration_hours: '10',
  rating: '0',
  price: '0',
  original_price: '0',
  offer_expires_at: '',
  kind: 'Course',
  is_demo: true,
  source_note: '',
};

export function OrganizationPage() {
  const { user, toast } = useWorkspace();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState('');
  const [modal, setModal] = useState<'course' | 'post' | null>(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState('');
  const [course, setCourse] = useState<CourseForm>({ ...blankCourse });
  const [post, setPost] = useState({
    text: '',
    source: '',
    source_url: '',
    published_at: '',
    is_demo: true,
  });
  async function load() {
    try {
      setOverview(await api<Overview>('/admin/overview'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const update = <K extends keyof CourseForm>(key: K, value: CourseForm[K]) =>
    setCourse((c) => ({ ...c, [key]: value }));
  async function ingest(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFormError('');
    try {
      if (modal === 'course') {
        const price = Number(course.price);
        const original = Number(course.original_price);
        await api('/admin/courses', 'POST', {
          ...course,
          skills: split(course.skills),
          duration_hours: Number(course.duration_hours),
          rating: Number(course.rating),
          price,
          original_price: original,
          discount_percent: original ? Math.round((1 - price / original) * 1000) / 10 : 0,
          currency: 'USD',
          offer_expires_at: course.offer_expires_at
            ? new Date(course.offer_expires_at).toISOString()
            : null,
        });
        setCourse({ ...blankCourse });
      } else {
        await api('/admin/posts', 'POST', {
          ...post,
          source_url: post.source_url || null,
          published_at: post.published_at
            ? new Date(post.published_at).toISOString()
            : new Date().toISOString(),
        });
        setPost({ text: '', source: '', source_url: '', published_at: '', is_demo: true });
      }
      setModal(null);
      await load();
      toast('Added to the shared knowledge base. Run the agents to use the new source.');
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function openModal(kind: 'course' | 'post') {
    setFormError('');
    setModal(kind);
  }
  if (error)
    return (
      <Empty
        title="Organization insights are unavailable."
        text={error}
        action={
          <button className="button secondary" onClick={() => void load()}>
            Try again
          </button>
        }
      />
    );
  if (!overview) return <Spinner label="Gathering organization insights…" />;
  const stats = [
    { title: 'Employees', value: overview.employee_count, icon: Users },
    { title: 'Active learners', value: overview.active_learners, icon: BookOpen },
    { title: 'Courses completed', value: overview.completed_courses, icon: CheckCheck },
    { title: 'Recommendations', value: overview.total_recommendations, icon: Sparkles },
  ];
  return (
    <>
      <PageHeading
        eyebrow="GROWTH IS A TEAM EFFORT"
        title="Organization"
        description="Aggregate employee training activity and catalogue management."
        action={
          <span className="workspace-badge">
            <Building2 size={15} />
            {user.role === 'admin' ? 'ADMIN WORKSPACE' : 'HR / L&D WORKSPACE'}
          </span>
        }
      />
      <div className="stat-grid">
        {stats.map((s, i) => (
          <section className="stat-card" key={s.title}>
            <div className="stat-label">
              {s.title}
              <span className={`stat-icon ${['green', 'purple', 'orange', 'blue'][i]}`}>
                <s.icon />
              </span>
            </div>
            <strong>{String(s.value).padStart(2, '0')}</strong>
            <p>Across this local organization</p>
          </section>
        ))}
      </div>
      <div className="organization-grid">
        <section className="card chart-panel">
          <PanelHeading
            title="Common skill gaps"
            sub="Skill gaps from employees’ most recent analyses."
          />
          {overview.top_skill_gaps.length ? (
            <div className="bar-chart">
              {overview.top_skill_gaps.map((item) => (
                <div key={item.skill}>
                  <span>{item.skill}</span>
                  <div className="progress-track">
                    <i
                      style={{
                        width: `${(item.count / Math.max(1, ...overview.top_skill_gaps.map((g) => g.count))) * 100}%`,
                      }}
                    />
                  </div>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="Learning insights start with discovery."
              text="Employee analysis runs will reveal aggregate skill gaps here."
            />
          )}
        </section>
        <section className="card chart-panel">
          <PanelHeading title="Employee roles" sub="Current role distribution across employees." />
          {overview.role_distribution.map((item) => (
            <div className="role-row" key={item.role}>
              <span className="role-icon">
                <Users size={17} />
              </span>
              <strong>{item.role}</strong>
              <span>
                {item.count} {item.count === 1 ? 'employee' : 'employees'}
              </span>
            </div>
          ))}
          <div className="info-box">
            <ShieldCheck size={18} />
            <p>
              These aggregate insights support training planning. They must not be used for
              promotions, performance scoring or hiring decisions.
            </p>
          </div>
        </section>
      </div>
      <section className="card knowledge-panel">
        <PanelHeading
          title="Knowledge base"
          sub="A traceable knowledge base for grounded recommendations."
        />
        <div className="knowledge-row">
          <div>
            <BookOpen size={24} />
            <strong>{overview.catalogue_count}</strong>
            <span>training opportunities</span>
          </div>
          <div>
            <FilePlus2 size={24} />
            <strong>{overview.post_count}</strong>
            <span>professional learning posts</span>
          </div>
          {user.role === 'admin' ? (
            <div className="knowledge-actions">
              <button className="button primary" onClick={() => openModal('course')}>
                <Plus size={16} />
                Add opportunity
              </button>
              <button className="button secondary" onClick={() => openModal('post')}>
                <Plus size={16} />
                Add learning content
              </button>
            </div>
          ) : (
            <p className="muted small">
              Administrators can add source-backed opportunities and professional learning content.
            </p>
          )}
        </div>
      </section>
      <PanelHeading
        title="Proposed subscription plans"
        sub="Commercialization concept · indicative pricing assumptions, not an active subscription."
      />
      <div className="pricing-grid">
        {overview.pricing.map((plan, i) => (
          <section className={`card pricing-card ${i === 1 ? 'featured' : ''}`} key={plan.name}>
            <span className="eyebrow">{plan.name}</span>
            <p className="plan-price">
              LKR {plan.price_lkr}
              <small> / employee / month</small>
            </p>
            <p>{plan.description}</p>
            <span className="pill">Proposed B2B SaaS plan</span>
          </section>
        ))}
      </div>
      {modal && (
        <Drawer
          title={
            modal === 'course' ? 'Add a learning opportunity' : 'Add professional learning content'
          }
          subtitle="SHARED KNOWLEDGE BASE"
          wide
          onClose={() => {
            if (!busy) setModal(null);
          }}
        >
          <form onSubmit={(e) => void ingest(e)} className="drawer-content ingestion-form">
            <p className="muted">
              Use content you have permission to include. Record the source and distinguish
              demonstration data from verified records.
            </p>
            {modal === 'course' ? (
              <div className="form-grid">
                <label className="full-width">
                  Opportunity title
                  <input
                    required
                    minLength={3}
                    maxLength={240}
                    value={course.title}
                    onChange={(e) => update('title', e.target.value)}
                  />
                </label>
                <label>
                  Provider
                  <input
                    required
                    maxLength={120}
                    value={course.provider}
                    onChange={(e) => update('provider', e.target.value)}
                  />
                </label>
                <label>
                  Type
                  <select value={course.kind} onChange={(e) => update('kind', e.target.value)}>
                    {['Course', 'Certification', 'Learning path'].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label className="full-width">
                  Provider source URL (HTTPS)
                  <input
                    type="url"
                    pattern="https://.*"
                    required
                    maxLength={2000}
                    placeholder="https://"
                    value={course.url}
                    onChange={(e) => update('url', e.target.value)}
                  />
                </label>
                <label className="full-width">
                  Description
                  <textarea
                    required
                    minLength={10}
                    maxLength={6000}
                    rows={3}
                    value={course.description}
                    onChange={(e) => update('description', e.target.value)}
                  />
                </label>
                <label className="full-width">
                  Skills covered (comma-separated)
                  <input
                    required
                    value={course.skills}
                    onChange={(e) => update('skills', e.target.value)}
                  />
                </label>
                <label>
                  Category
                  <input
                    required
                    maxLength={120}
                    value={course.category}
                    onChange={(e) => update('category', e.target.value)}
                  />
                </label>
                <label>
                  Level
                  <select value={course.level} onChange={(e) => update('level', e.target.value)}>
                    {['Beginner', 'Intermediate', 'Advanced'].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Duration (hours)
                  <input
                    type="number"
                    min="0.1"
                    step="0.1"
                    max={5000}
                    required
                    value={course.duration_hours}
                    onChange={(e) => update('duration_hours', e.target.value)}
                  />
                </label>
                <label>
                  Rating (0 means unrated)
                  <input
                    type="number"
                    min="0"
                    max="5"
                    step="0.1"
                    required
                    value={course.rating}
                    onChange={(e) => update('rating', e.target.value)}
                  />
                </label>
                <label>
                  Current price (USD)
                  <input
                    type="number"
                    min="0"
                    max={100000}
                    step="0.01"
                    required
                    value={course.price}
                    onChange={(e) => update('price', e.target.value)}
                  />
                </label>
                <label>
                  Original price (USD)
                  <input
                    type="number"
                    min="0"
                    max={100000}
                    step="0.01"
                    required
                    value={course.original_price}
                    onChange={(e) => update('original_price', e.target.value)}
                  />
                </label>
                <label className="full-width">
                  Offer expiry{' '}
                  {Number(course.original_price) > Number(course.price) &&
                    '(required for a discount)'}
                  <input
                    type="datetime-local"
                    required={Number(course.original_price) > Number(course.price)}
                    value={course.offer_expires_at}
                    onChange={(e) => update('offer_expires_at', e.target.value)}
                  />
                  <small>Discount percentage is calculated from the two prices.</small>
                </label>
                <label className="full-width">
                  Source and verification note
                  <textarea
                    required
                    minLength={5}
                    maxLength={1000}
                    rows={2}
                    placeholder="Where this record came from, when checked, and any sample values"
                    value={course.source_note}
                    onChange={(e) => update('source_note', e.target.value)}
                  />
                </label>
                <label className="checkbox-label full-width">
                  <input
                    type="checkbox"
                    checked={course.is_demo}
                    onChange={(e) => update('is_demo', e.target.checked)}
                  />
                  This record contains demonstration data
                </label>
              </div>
            ) : (
              <div className="form-grid">
                <label className="full-width">
                  Learning content
                  <textarea
                    required
                    minLength={10}
                    maxLength={10000}
                    rows={6}
                    value={post.text}
                    onChange={(e) => setPost((p) => ({ ...p, text: e.target.value }))}
                  />
                </label>
                <label className="full-width">
                  Source / author label
                  <input
                    required
                    maxLength={200}
                    value={post.source}
                    onChange={(e) => setPost((p) => ({ ...p, source: e.target.value }))}
                  />
                </label>
                <label className="full-width">
                  Source URL (optional, HTTPS)
                  <input
                    type="url"
                    pattern="https://.*"
                    maxLength={2000}
                    value={post.source_url}
                    onChange={(e) => setPost((p) => ({ ...p, source_url: e.target.value }))}
                  />
                </label>
                <label className="full-width">
                  Published at (leave empty for now)
                  <input
                    type="datetime-local"
                    value={post.published_at}
                    onChange={(e) => setPost((p) => ({ ...p, published_at: e.target.value }))}
                  />
                </label>
                <label className="checkbox-label full-width">
                  <input
                    type="checkbox"
                    checked={post.is_demo}
                    onChange={(e) => setPost((p) => ({ ...p, is_demo: e.target.checked }))}
                  />
                  This is synthetic demonstration content
                </label>
              </div>
            )}
            {formError && (
              <p className="form-error" role="alert">
                {formError}
              </p>
            )}
            <div className="form-actions">
              <button className="button primary" disabled={busy}>
                <Plus size={17} />
                {busy ? 'Adding source…' : 'Add to knowledge base'}
              </button>
            </div>
          </form>
        </Drawer>
      )}
    </>
  );
}
