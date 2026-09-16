# SkillScout AI — implementation contract

This local, from-scratch project implements the user's employee-training system. All code is original for this project. Use Python 3.12+ / FastAPI / SQLite and React + TypeScript + Vite. No cloud accounts required for the core demo. Integrate Ollama and optionally a generic OpenAI-compatible endpoint for actual LLM inference, clearly expose whether inference is available. Never label a deterministic fallback as an LLM. No scraped LinkedIn/private data. Seed posts are synthetic; catalogue courses use real provider URLs and any sample prices/offers are explicitly demonstration data, not verified live prices.

## Ownership
- Root: scaffolding/dev runner/install, docs, integration fixes, acceptance tests and browser QA.
- AI agent implementer: `backend/ai/`, `backend/data/`, `backend/evaluation.py`, `tests/test_ai.py`. No changes outside these without coordination.
- API implementer: `backend/api.py`, `backend/db.py`, `backend/security.py`, `backend/worker.py`, `backend/config.py`, `backend/__init__.py`, `tests/test_api.py`. Own runtime/db orchestration. No frontend changes.
- UI implementer: `frontend/` only. Own all frontend setup and code; root installs dependencies.

## Shared conventions
UTC ISO timestamps; snake_case JSON; UUID ids. All currency USD (display currency explicitly). API under `/api`. Vite proxies `/api` to localhost:8000. API serves `frontend/dist` for built production single origin. Browser auth HttpOnly SameSite=Lax session cookie; unsafe API requests require `X-CSRF-Token` obtained from login/session. Passwords PBKDF2/scrypt; SQLite sessions hashed. Responses are plain JSON. Errors `{detail: string}`. No external mail delivery, only in-app notifications. External links use https, target blank, noopener. Frontend uses icon library lucide-react and custom CSS. No placeholder buttons.

## Core objects
User `{id,name,email,role:employee|hr|admin}`
Profile `{user_id,role_title,career_goal,experience_years,skills:string[],certifications:string[],training_history:string[],weekly_hours:number,budget:number,interests:string[],bio:string,notifications_enabled:boolean,consent:boolean}`
Course `{id,title,provider,url,description,skills:string[],category,level:Beginner|Intermediate|Advanced,duration_hours:number,rating:number,price:number,original_price:number,currency:'USD',discount_percent:number,offer_expires_at:string|null,kind:Course|Certification|Learning path,is_demo:boolean,source_note:string}`
Post `{id,text,source,source_url:string|null,published_at:string,is_demo:boolean}`
Trend `{skill,mentions:number,growth_percent:number,score:number,summary:string,evidence:[{id,text,source,source_url,published_at}],related_skills:string[]}`. Growth based on current vs prior observation window; disclose sparse synthetic data.
Needs `{current_role,career_goal,current_skills:string[],target_skills:string[],skill_gaps:string[],priority_skills:string[],summary,llm_used:boolean,model:string|null}`
Recommendation `{id,course:Course,score:number,factors:{profile_relevance,career_alignment,skill_gap_relevance,trend_relevance,discount_value},explanation:string,matched_skills:string[],priority:high|medium|low,generated_at:string,source_ids:string[]}`. Scores and factors in 0–100. Ground explanations in course and needs. Enforce stale offer handling and prerequisites/level suitability. Recommendation id can equal course id.
Notification `{id,title,message,course_id:string|null,created_at,read:boolean,kind:opportunity|system}`
Saved item `{course:Course,status:saved|in_progress|completed,saved_at:string,completed_at:string|null}`
Run `{id,status:running|completed|failed,started_at,finished_at,error:string|null,steps:[{agent:string,label:string,status:pending|running|completed|failed,duration_ms:number,input:object,output:object,error:string|null}]}`
Agent metadata `{id,name,port,status,description}`

## Browser REST contract
- `GET /api/health` public: `{status,version}`
- `POST /api/auth/login` `{email,password}` -> `{user,csrf_token}` + cookie
- `POST /api/auth/register` `{name,email,password}` -> `{user,csrf_token}`; employees only; creates default profile with consent false
- `GET /api/auth/session` -> `{user,csrf_token}` or 401
- `POST /api/auth/logout` -> `{ok:true}`
- `GET /api/profile` -> Profile
- `PUT /api/profile` -> Profile; same editable fields as Profile, user_id ignored or rejected. Enforce ranges, lengths, arrays; consent required to run analysis.
- `GET /api/dashboard` -> `{profile,needs:Needs|null,recommendations:Recommendation[],trends:Trend[],stats:{recommendations,skill_gaps,saved_courses,completed_courses,unread_notifications},last_run:Run|null,mode:{llm_available:boolean,provider:string,model:string,description:string}}`
- `POST /api/runs` body `{}` -> Run (awaits completion, up to 120s). Uses authenticated employee profile. On error return saved failed Run with status failed, not silent local bypass.
- `GET /api/runs` -> Run[] last 20 scoped to user
- `GET /api/runs/{id}` -> Run scoped to user
- `GET /api/courses?q=&category=&level=&kind=&free_only=false` -> Course[]; hybrid search if query provided.
- `GET /api/courses/{id}` -> Course
- `GET /api/recommendations` -> Recommendation[]
- `GET /api/trends` -> `{trends:Trend[],posts:Post[],corpus_note:string}`
- `GET /api/learning-plan` -> Saved item[]
- `PUT /api/learning-plan/{course_id}` `{status:saved|in_progress|completed}` -> Saved item
- `DELETE /api/learning-plan/{course_id}` -> `{ok:true}`
- `GET /api/notifications` -> Notification[]
- `POST /api/notifications/{id}/read` -> `{ok:true}` (use `all` for all)
- `GET /api/system` -> `{agents:Agent[],mode:Mode,scheduler:{enabled:boolean,interval_minutes:number,last_checked_at:string|null},catalogue_count:number,post_count:number}`
- `POST /api/chat` `{message:string}` -> `{answer:string,sources:Course[],llm_used:boolean,model:string|null}`. Employee profile allowed only current user's. Grounded RAG; no invented course IDs/discounts. Length caps.
- `GET /api/privacy/export` -> `{user,profile,learning_plan,runs,notifications}` excludes password/session secrets.
- `DELETE /api/privacy/account` `{password:string}` -> `{ok:true}` remove private user data and sessions. Last admin protected.
- `GET /api/admin/overview` HR/admin only -> `{employee_count,active_learners,completed_courses,total_recommendations,top_skill_gaps:[{skill,count}],role_distribution:[{role,count}],catalogue_count,post_count,pricing:[{name,price_lkr,description}]}`. Aggregates, no private individual career profiles.
- `POST /api/admin/courses` admin only, Course editable fields (id generated) -> Course. Validate https URL and fields. `is_demo` explicit.
- `POST /api/admin/posts` admin only `{text,source,source_url?,published_at?,is_demo:boolean}` -> Post

## Seed credentials and experience
`alex@skillscout.demo` / `SkillScout123!` employee, Alex Morgan, Data Analyst → Data Scientist, skills SQL/Excel/Power BI, 3 years, 6 hours/week, budget $80.
`hr@skillscout.demo` / `SkillScout123!` HR, Jordan Lee.
`admin@skillscout.demo` / `SkillScout123!` admin, Sam Taylor.
Demo login screen should offer role selection and autofill or explicit sign-in as demo user. Never auto-login silently.

## AI module contract (sync Python, no DB)
`backend.ai.engine.analyze_profile(profile:dict) -> Needs`
`backend.ai.engine.discover_trends(posts:list[dict], needs:dict|None = None) -> list[Trend]`
`backend.ai.engine.retrieve_courses(courses:list[dict], needs:dict, trends:list[dict], query:str|None = None, limit:int = 12) -> list[dict]` results `{course:Course,retrieval_score:float,matched_skills:list[str]}`
`backend.ai.engine.recommend(profile:dict, needs:dict, trends:list[dict], candidates:list[dict]) -> list[Recommendation]`
`backend.ai.engine.answer_question(message:str,profile:dict,courses:list[dict],needs:dict|None=None) -> {answer,sources,llm_used,model}`
`backend.ai.engine.get_model_status() -> {llm_available,provider,model,description}` use short timeout/cache.
`backend.data.seed.get_seed_courses()`, `get_seed_posts()` -> lists with dates relative to UTC now, clearly marked demo; several career tracks and at least 24 rich course records, at least 35 posts. Data uses stable IDs.
Engine should have genuine hybrid IR (BM25 + TF-IDF/cosine, normalised weighted score), NLP entity/keyphrase extraction, observable decision-making, actual HTTP LLM integration with robust validated/factual grounding, transparent offline fallback. Prefer standard lib + numpy; avoid heavyweight dependencies where not needed. Provide labeled small retrieval evaluation dataset and repeatable P@k, recall@k, MRR, NDCG evaluation, honest limitations. Include injection boundary for content.

## Four HTTP agent services (owned by API implementer)
One `backend.worker:app` with `AGENT_KIND=profile|trends|retrieval|recommendations`, launched independently on ports 8101,8102,8103,8104. Service endpoint `POST /execute` requires `X-Agent-Key` set by launcher environment, and `GET /health` returns kind. JSON envelope `{run_id,user_id,payload:dict}`; output `{run_id,agent,result:dict|list}`. Gateway orchestrates via httpx, passes typed JSON between services, captures durations and failure traces, sequential dependencies with retries only for transient connection failures. HTTP internal auth. Bind 127.0.0.1 default. Define environment/config defaults in backend/config.py.
profile payload `{profile}`
trends payload `{posts,needs}`
retrieval payload `{courses,needs,trends}`
recommendations payload `{profile,needs,trends,candidates}`

## UI direction
Premium editorial workspace: warm off-white background, near-black type, deep forest-green accent, pale lime highlights. Fixed 240px left sidebar with brand mark, workspace selector, small uppercase nav grouping, active pale green nav, profile bottom. Main generous whitespace, thin borders, minimal shadows, rounded 14–18px cards. Top breadcrumbs/date/notifications. Dashboard overline 'YOUR LEARNING, IN FOCUS', large warm welcome and clear goal, prominent 'Find opportunities' action, four quiet stat cards, two-column recommendations + career path/trending skills, visually informative progress graph/rings without distracting charts. Abstract geometric CSS illustration in hero optional. Course provider monogram tiles, category chips, match percentage green badge, exact offer disclaimer. No random stock images required. Responsive mobile sidebar, accessible labels/focus and real loading/empty/error states. Pages: Overview, Explore courses, Learning plan, Learning trends, Agent workspace, Profile & settings, notifications tray; HR/admin 'Organization'; Admin data-ingestion tab. Course details drawer with why, score breakdown, source, save/open actions. Grounded 'Ask Scout' chat drawer.

## Verification expectations
Meaningful tests for retrieval ranking, scoring, expired offers, grounding/fallback, login + CSRF + access boundaries, role checks, consent, saved-course transitions, worker key. Root runs full HTTP pipeline and browser flows. README with installation, one-command startup, LLM setup, demo, architecture, security limits, dataset provenance and report/viva guidance. No claim of production readiness or untested integrations.
