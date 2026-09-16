import { ArrowRight } from 'lucide-react';
import { CourseCard, Empty, PanelHeading, RunButton, Tags } from './components';
import { useWorkspace } from './workspace';

export default function DashboardPage() {
  const { user, dashboard: d, go } = useWorkspace();
  const stats = [
    { label: 'Recommendations', value: d.stats.recommendations, page: 'explore' as const },
    { label: 'Skill gaps', value: d.stats.skill_gaps, page: 'settings' as const },
    { label: 'Saved courses', value: d.stats.saved_courses, page: 'plan' as const },
    { label: 'Completed', value: d.stats.completed_courses, page: 'plan' as const },
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Overview</h1>
          <p className="muted">
            Welcome, {user.name.split(' ')[0]}. Here is your learning summary.
          </p>
        </div>
        <RunButton />
      </div>
      <div className="goal-summary">
        <div>
          <span>Current role</span>
          <strong>{d.profile.role_title || 'Add your role'}</strong>
        </div>
        <ArrowRight size={18} aria-hidden="true" />
        <div>
          <span>Career goal</span>
          <strong>{d.profile.career_goal || 'Set a career goal'}</strong>
        </div>
        <button className="text-button" onClick={() => go('settings')}>
          Edit profile
        </button>
      </div>
      {!d.profile.consent && (
        <div className="notice warm">
          <p>Complete your profile and enable learning analysis to get recommendations.</p>
          <button className="text-button" onClick={() => go('settings')}>
            Set up profile
          </button>
        </div>
      )}
      <div className="stat-grid">
        {stats.map((stat) => (
          <button className="stat-card" key={stat.label} onClick={() => go(stat.page)}>
            <span className="stat-label">{stat.label}</span>
            <strong>{stat.value}</strong>
          </button>
        ))}
      </div>
      <div className="dashboard-columns">
        <section className="dashboard-main">
          <PanelHeading
            title="Recommended courses"
            sub="Based on your profile and learning goals."
            action={
              <button className="text-button" onClick={() => go('explore')}>
                Browse all
              </button>
            }
          />
          {d.recommendations.length ? (
            <div className="recommendation-grid">
              {d.recommendations.slice(0, 4).map((rec) => (
                <CourseCard key={rec.id} course={rec.course} rec={rec} />
              ))}
            </div>
          ) : (
            <div className="card">
              <Empty
                title="No recommendations yet"
                text="Select Find opportunities to run the four agents."
              />
            </div>
          )}
          <p className="data-caption">
            Demo catalogue: prices, ratings and offers are sample data. Check the provider for
            current details.
          </p>
        </section>
        <aside className="dashboard-aside">
          <section className="card simple-side-card">
            <PanelHeading title="Skills to focus on" />
            {d.needs?.priority_skills.length ? (
              <ol className="priority-list">
                {d.needs.priority_skills.map((skill) => (
                  <li key={skill}>{skill}</li>
                ))}
              </ol>
            ) : (
              <p className="muted">Run discovery to identify your skill gaps.</p>
            )}
            <p className="small muted">Current skills</p>
            <Tags values={d.profile.skills} limit={6} />
          </section>
          <section className="card simple-side-card">
            <PanelHeading title="Learning trends" />
            <div className="simple-trends">
              {d.trends.slice(0, 3).map((trend) => (
                <button key={trend.skill} onClick={() => go('trends')}>
                  <strong>{trend.skill}</strong>
                  <span>{trend.mentions} mentions</span>
                </button>
              ))}
            </div>
            <button className="text-button" onClick={() => go('trends')}>
              View evidence
            </button>
            <p className="data-caption">From the supplied learning-content corpus.</p>
          </section>
        </aside>
      </div>
    </>
  );
}
