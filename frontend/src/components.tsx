import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import {
  ArrowRight,
  Bookmark,
  Check,
  Clock3,
  ExternalLink,
  LoaderCircle,
  Sparkles,
  Star,
  X,
} from 'lucide-react';
import { date, money } from './api';
import type { Course, Recommendation } from './types';
import { useWorkspace } from './workspace';

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <div className={`brand ${light ? 'brand-light' : ''}`}>
      <span className="brand-symbol">
        <span />
        <span />
        <span />
        <span />
      </span>
      <span>
        skillscout<span className="brand-ai">AI</span>
      </span>
    </div>
  );
}
export function Spinner({ label = 'Loading your workspace…' }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={24} />
      <span>{label}</span>
    </div>
  );
}
export function Empty({
  icon,
  title,
  text,
  action,
}: {
  icon?: ReactNode;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon || <Sparkles size={25} />}</div>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action}
    </div>
  );
}
export function PanelHeading({
  title,
  sub,
  action,
}: {
  title: string;
  sub?: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel-heading">
      <div>
        <h2>{title}</h2>
        {sub && <p className="muted">{sub}</p>}
      </div>
      {action}
    </div>
  );
}
export function Provider({ provider, large = false }: { provider: string; large?: boolean }) {
  const colors = ['blue', 'teal', 'purple', 'orange'];
  let n = 0;
  for (const c of provider) n += c.charCodeAt(0);
  return (
    <div
      className={`provider-tile ${colors[n % colors.length]} ${large ? 'large' : ''}`}
      aria-hidden="true"
    >
      {provider.toLowerCase().includes('microsoft') ? (
        <span className="microsoft-grid">
          <i />
          <i />
          <i />
          <i />
        </span>
      ) : provider.toLowerCase().includes('coursera') ? (
        'c'
      ) : provider.toLowerCase().includes('google') ? (
        'G'
      ) : provider.toLowerCase().includes('aws') ? (
        'aws'
      ) : provider.toLowerCase().includes('udemy') ? (
        'u'
      ) : (
        provider
          .replace(/[^a-z]/gi, '')
          .slice(0, 2)
          .toUpperCase()
      )}
    </div>
  );
}
export function Tags({ values, limit = 4 }: { values: string[]; limit?: number }) {
  return (
    <div className="tags">
      {values.slice(0, limit).map((v) => (
        <span className="tag" key={v}>
          {v}
        </span>
      ))}
      {values.length > limit && <span className="tag">+{values.length - limit}</span>}
    </div>
  );
}
export function RunButton({ compact = false }: { compact?: boolean }) {
  const { run, running } = useWorkspace();
  return (
    <button className="button primary" onClick={() => void run()} disabled={running}>
      {running ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}{' '}
      {running ? 'Agents are working…' : compact ? 'Run agents' : 'Find opportunities'}
      {!running && !compact && <ArrowRight size={16} />}
    </button>
  );
}
export function CourseCard({
  course,
  rec,
  compact = false,
}: {
  course: Course;
  rec?: Recommendation;
  compact?: boolean;
}) {
  const { saved, save, selectCourse } = useWorkspace();
  const isSaved = saved.some((s) => s.course.id === course.id);
  const validOffer =
    course.discount_percent > 0 &&
    (!course.offer_expires_at || new Date(course.offer_expires_at) > new Date());
  return (
    <article className={`course-card ${compact ? 'compact' : ''}`}>
      <div className="course-top">
        <Provider provider={course.provider} />
        <span className="course-kind">{course.kind}</span>
        <button
          className={`icon-button save-button ${isSaved ? 'selected' : ''}`}
          aria-label={isSaved ? `${course.title} is saved` : `Save ${course.title}`}
          title={isSaved ? 'Added to learning plan' : 'Save to learning plan'}
          onClick={() => void save(course)}
          disabled={isSaved}
        >
          {isSaved ? <Bookmark size={19} fill="currentColor" /> : <Bookmark size={19} />}
        </button>
      </div>
      <p className="provider-name">{course.provider}</p>
      <button className="course-title" onClick={() => selectCourse(course, rec)}>
        {course.title}
      </button>
      <div className="course-meta">
        <span>
          <Clock3 size={13} />
          {course.duration_hours} hours
        </span>
        <span className="meta-dot">·</span>
        <span>{course.level}</span>
        {course.rating > 0 && (
          <>
            <span className="meta-dot">·</span>
            <span>
              <Star size={13} className="star" fill="currentColor" />
              {course.rating.toFixed(1)}
            </span>
          </>
        )}
      </div>
      <Tags values={rec?.matched_skills.length ? rec.matched_skills : course.skills} limit={3} />
      {rec && (
        <p className="course-reason">
          <Sparkles size={13} />
          <span>{rec.explanation}</span>
        </p>
      )}
      <div className="course-bottom">
        <div>
          <span className="course-price">{money(course.price)}</span>
          {validOffer && course.original_price > course.price && (
            <span className="old-price">{money(course.original_price)}</span>
          )}
          {validOffer && <span className="offer-badge">−{course.discount_percent}%</span>}
        </div>
        {rec ? (
          <button className="match-badge" onClick={() => selectCourse(course, rec)}>
            <span className="status-dot" />
            {Math.round(rec.score)}% match <ArrowRight size={13} />
          </button>
        ) : (
          <button className="text-button" onClick={() => selectCourse(course)}>
            Details <ArrowRight size={14} />
          </button>
        )}
      </div>
      <div className="price-note">
        {course.is_demo ? 'Demo price' : 'Listed price'}
        {course.price > 0 ? ' · USD' : ''}
        {validOffer && course.offer_expires_at
          ? ` · Offer ends ${date(course.offer_expires_at)}`
          : ''}
      </div>
    </article>
  );
}
export function Drawer({
  title,
  subtitle,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeRef.current();
      if (event.key === 'Tab') {
        const buttons = panel.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input, select, textarea, [tabindex="0"]',
        );
        if (!buttons?.length) return;
        const first = buttons[0];
        const last = buttons[buttons.length - 1];
        if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === panel.current)
        ) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener('keydown', onKey);
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="drawer-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className={`drawer ${wide ? 'drawer-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={panel}
      >
        <div className="drawer-heading">
          <div>
            <p className="eyebrow">{subtitle || 'SKILLSCOUT AI'}</p>
            <h2>{title}</h2>
          </div>
          <button className="icon-button" aria-label="Close panel" onClick={onClose}>
            <X />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
export function CourseDetail({
  course,
  rec,
  onClose,
}: {
  course: Course;
  rec?: Recommendation;
  onClose: () => void;
}) {
  const { save, saved } = useWorkspace();
  const item = saved.find((s) => s.course.id === course.id);
  return (
    <Drawer title="A closer look" subtitle="LEARNING OPPORTUNITY" onClose={onClose}>
      <div className="drawer-content">
        <Provider provider={course.provider} large />
        <p className="provider-name">
          {course.provider} <span> / {course.kind}</span>
        </p>
        <h2 className="detail-title">{course.title}</h2>
        <p className="detail-description">{course.description}</p>
        <Tags values={course.skills} limit={20} />
        <div className="detail-facts">
          <div>
            <span>Time commitment</span>
            <strong>{course.duration_hours} hours</strong>
          </div>
          <div>
            <span>Experience level</span>
            <strong>{course.level}</strong>
          </div>
          <div>
            <span>Listed price</span>
            <strong>
              {money(course.price)}
              {course.price > 0 ? ' USD' : ''}
            </strong>
          </div>
          <div>
            <span>Provider rating</span>
            <strong>{course.rating > 0 ? `${course.rating} / 5` : 'Not rated'}</strong>
          </div>
        </div>
        {rec ? (
          <section className="why-box">
            <div className="section-label">
              <Sparkles size={17} />
              <h3>Why this fits you</h3>
              <strong>{Math.round(rec.score)}%</strong>
            </div>
            <p>{rec.explanation}</p>
            <div className="score-factors">
              {Object.entries(rec.factors).map(([key, value]) => (
                <div key={key}>
                  <span>
                    {key.replaceAll('_', ' ')}
                    {rec.factor_weights?.[key] !== undefined && (
                      <small> · {Math.round(rec.factor_weights[key] * 100)}% weight</small>
                    )}
                  </span>
                  <div className="progress-track">
                    <i style={{ width: `${Math.min(value, 100)}%` }} />
                  </div>
                  <strong>{Math.round(value)}%</strong>
                </div>
              ))}
            </div>
            <small>Scores are explainable ranking estimates, not guarantees of outcomes.</small>
          </section>
        ) : (
          <div className="info-box">
            <Sparkles size={18} />
            <p>
              Run the four agents to see how this opportunity fits your current skills and career
              goal.
            </p>
          </div>
        )}
        <section className="source-section">
          <h3>Source & price transparency</h3>
          <p>
            {course.source_note ||
              'Course information is provided by the local training catalogue.'}
          </p>
          {course.is_demo && (
            <p>
              Prices, ratings and offers in this demonstration catalogue are sample data. Verify
              details on the provider’s website before enrolling.
            </p>
          )}
          <a href={course.url} target="_blank" rel="noopener noreferrer">
            View original provider source <ExternalLink size={14} />
          </a>
          {course.offer_expires_at && (
            <p>
              Listed offer expiry: {new Date(course.offer_expires_at).toLocaleString()}
              {new Date(course.offer_expires_at) < new Date() ? ' (expired)' : ''}.
            </p>
          )}
        </section>
      </div>
      <div className="drawer-footer">
        <button className="button primary" disabled={!!item} onClick={() => void save(course)}>
          {item ? <Check size={17} /> : <Bookmark size={17} />}{' '}
          {item ? 'In your learning plan' : 'Add to learning plan'}
        </button>
        <a className="button secondary" href={course.url} target="_blank" rel="noopener noreferrer">
          Visit provider <ExternalLink size={15} />
        </a>
      </div>
    </Drawer>
  );
}
