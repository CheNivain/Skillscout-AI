export type User = { id: string; name: string; email: string; role: 'employee' | 'hr' | 'admin' };
export type Profile = {
  user_id: string;
  role_title: string;
  career_goal: string;
  experience_years: number;
  skills: string[];
  certifications: string[];
  training_history: string[];
  weekly_hours: number;
  budget: number;
  interests: string[];
  bio: string;
  notifications_enabled: boolean;
  consent: boolean;
};
export type Course = {
  id: string;
  title: string;
  provider: string;
  url: string;
  description: string;
  skills: string[];
  category: string;
  level: string;
  duration_hours: number;
  rating: number;
  price: number;
  original_price: number;
  currency: string;
  discount_percent: number;
  offer_expires_at: string | null;
  kind: string;
  is_demo: boolean;
  source_note: string;
};
export type Post = {
  id: string;
  text: string;
  source: string;
  source_url: string | null;
  published_at: string;
  is_demo: boolean;
};
export type Trend = {
  skill: string;
  mentions: number;
  growth_percent: number;
  score: number;
  summary: string;
  evidence: Post[];
  related_skills: string[];
};
export type Needs = {
  current_role: string;
  career_goal: string;
  current_skills: string[];
  target_skills: string[];
  skill_gaps: string[];
  priority_skills: string[];
  summary: string;
  llm_used: boolean;
  model: string | null;
};
export type Recommendation = {
  id: string;
  course: Course;
  score: number;
  factors: Record<string, number>;
  factor_weights?: Record<string, number>;
  explanation: string;
  matched_skills: string[];
  priority: string;
  generated_at: string;
  source_ids: string[];
};
export type Notification = {
  id: string;
  title: string;
  message: string;
  course_id: string | null;
  created_at: string;
  read: boolean;
  kind: string;
};
export type Saved = {
  course: Course;
  status: 'saved' | 'in_progress' | 'completed';
  saved_at: string;
  completed_at: string | null;
};
export type Step = {
  agent: string;
  label: string;
  status: string;
  duration_ms: number;
  input: unknown;
  output: unknown;
  error: string | null;
};
export type Run = {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
  steps: Step[];
};
export type Mode = { llm_available: boolean; provider: string; model: string; description: string };
export type Agent = { id: string; name: string; port: number; status: string; description: string };
export type System = {
  agents: Agent[];
  mode: Mode;
  scheduler: { enabled: boolean; interval_minutes: number; last_checked_at: string | null };
  catalogue_count: number;
  post_count: number;
};
export type Dashboard = {
  profile: Profile;
  needs: Needs | null;
  recommendations: Recommendation[];
  trends: Trend[];
  stats: {
    recommendations: number;
    skill_gaps: number;
    saved_courses: number;
    completed_courses: number;
    unread_notifications: number;
  };
  last_run: Run | null;
  mode: Mode;
};
export type Overview = {
  employee_count: number;
  active_learners: number;
  completed_courses: number;
  total_recommendations: number;
  top_skill_gaps: { skill: string; count: number }[];
  role_distribution: { role: string; count: number }[];
  catalogue_count: number;
  post_count: number;
  pricing: { name: string; price_lkr: number; description: string }[];
};
export type ChatResponse = {
  answer: string;
  sources: Course[];
  llm_used: boolean;
  model: string | null;
};
