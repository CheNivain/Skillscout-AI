# SkillScout AI — speaker notes

Main presentation: slides 1–20. Backup: slides 21–30. Allow 15–18 minutes including the live demo.

## 1. SkillScout AI

OPENING, about 25 seconds
Good morning. We are presenting SkillScout AI, a local employee learning assistant. It helps an employee identify what to learn next and find relevant training opportunities. Our implementation combines four specialized agent services, local language-model assistance, NLP, information retrieval and security. We will explain the workflow and then demonstrate how an employee uses it.

The names identify the presenters. They do not assign authorship of individual components. Each member should explain their actual contribution when asked.

Sources: Group Assignment Brief.pdf, pp. 1–4; README.md; user-supplied presenter names. Cover: AI-generated conceptual artwork, built-in image tool. Prompt: four translucent green glass volumes on ascending stone steps connected by a ribbon, ivory background, clean left space, no text.

## 2. The employee training problem

EXPLAIN, about 30 seconds
Imagine an employee who already knows SQL and Excel but wants to become a data scientist. There are many courses, but the employee has to decide which skills are missing and which course is worth their time. They may browse LinkedIn and then search several course platforms. Our problem is personalized discovery. We do not claim that our prototype has measured time savings yet. The problem statement comes from our project proposal.

Sources: User-supplied domain and problem statement.

## 3. SkillScout at a glance

EXPLAIN, about 30 seconds
The employee gives the system a professional profile and career goal. Four services then identify needs, extract trends, retrieve course candidates and rank them. The bundled dataset contains 32 course records and 42 synthetic learning posts. These are a controlled demonstration dataset. The prototype does not scrape LinkedIn or retrieve live discounts from course websites. Prices, ratings and durations should be checked at the provider before a real decision.

Sources: backend/config.py:14; backend/data/seed.py; README.md, Model and data provenance.

## 4. One employee, one learning goal

EXPLAIN, about 35 seconds
For our example, the employee is a data analyst with SQL, Excel and Power BI. The goal is data scientist. In the current taxonomy, that exact combination produces five gaps: Python, Statistics, Machine Learning, Pandas and Data Visualization. The role and goal produce target skills, and skills already present are removed. Time and budget influence later ranking. These values are a demonstration scenario. The actual user account may have different profile details, so set them before the viva if this is the example you choose. Leave extra interests and biography empty if you want this exact gap set.

Sources: backend/ai/engine.py:281; backend/ai/taxonomy.py:47.

## 5. System architecture

EXPLAIN, about 50 seconds
The React frontend is the interface. It sends API requests through the FastAPI gateway on port 8000. The gateway reads SQLite and coordinates the four independent worker processes on ports 8101 to 8104. All four share reusable engine code but run a different handler according to AGENT_KIND. The profile worker and the grounded chat feature can call Ollama on port 11434. Workers communicate with the gateway using HTTP and JSON, authenticated by X-Agent-Key. The diagram is a logical overview. The gateway orchestrates a fixed sequence, so describe this as a bounded agent workflow.

Sources: scripts/dev.py; backend/api.py, _execute_pipeline; backend/config.py:14; backend/worker.py:87. Diagram: AI-generated explanatory image, checked against these code paths.

## 6. The four agent handoffs

EXPLAIN, about 35 seconds
Each agent has a narrow responsibility and a defined input and output. The gateway keeps the shared context. It first sends the employee profile to agent one, then sends its training needs along with posts to agent two. Agent three receives those needs, trends and the course catalogue. Agent four combines everything and ranks courses. The gateway saves the analysis and delivers eligible in-app notifications. A run ID lets us associate responses with the correct execution. The trace stores useful summaries, not every full raw payload.

Sources: backend/api.py, _execute_pipeline; backend/worker.py, Envelope and execute; CONTRACT.md.

## 7. Agent 1: profile and training needs

EXPLAIN, about 40 seconds
This agent answers, what does this employee need to learn? Normalize means converting different names for the same skill into a common name. Target skills come from curated role mappings and the employee’s interests or bio. A gap is a target skill the employee does not already have. The optional model receives only the valid gap list and prerequisite information, and proposes up to five priorities as JSON. The code checks the response, rejects unknown or duplicate skills, and enforces prerequisite order. If the model is unavailable or invalid, deterministic priorities remain and llm_used is false.

Sources: backend/ai/engine.py:281; backend/ai/taxonomy.py:47,77.

## 8. Agent 2: learning trend discovery

EXPLAIN, about 40 seconds
NLP means processing human language. Here we use dictionary-based entity extraction: find known names in text while handling aliases and word boundaries. In the example, the certification name can be recognized. The trend function counts each skill once per post, compares the last 14 days with the previous 14 days and keeps evidence snippets. It also finds skills that occur together. It returns up to ten trends. This is a transparent lightweight NLP method. It is not a trained neural NER model. The posts are synthetic, and their saved timestamps age normally.

Sources: backend/ai/engine.py:330; backend/ai/taxonomy.py:86,112,121; backend/data/seed.py.

## 9. Agent 3: training opportunity retrieval

EXPLAIN, about 50 seconds
Information retrieval selects useful existing records from a collection. We construct a query from priorities, gaps, the goal and relevant trend skills. Each course becomes searchable text containing its title, description, provider and skills. BM25 scores useful keyword matches with term-frequency saturation and document-length normalization. TF-IDF cosine compares sparse vectors of weighted terms. The code normalizes each score and combines 62% BM25 with 38% cosine. It then uses 88% of that hybrid score plus 12% skill coverage. This uses lexical features, not neural embeddings or a vector database. Course facts come from the catalogue.

Sources: backend/ai/engine.py:222,266,385.

## 10. Agent 4: recommendations and priorities

EXPLAIN, about 45 seconds
This agent combines five explicit factors. Skill gap has the largest weight at 30%. Profile fit and career alignment are each 25%, trends 15% and discount value 5%. It first removes duplicates, completed courses and courses with no relevant skill match. Advanced courses with missing prerequisites are excluded. Budget, level and available study time affect fit. High priority starts at 78, medium at 58. The gateway’s notice filter requires high priority and a score of at least 75, so effective eligibility starts at 78 under current scoring. Notifications also require the user’s setting. Ratings are displayed catalogue data but are not a scoring factor.

Sources: backend/ai/engine.py:436,440; backend/api.py, _notices_from.

## 11. The role of the local language model

EXPLAIN, about 40 seconds
We use a local model through Ollama. The default model name is qwen2.5:3b, but configuration can change it. The model makes bounded choices. In profile planning it proposes priorities from existing gaps. In Ask Scout it chooses valid course IDs from retrieved candidates and an allowed focus category. The application checks those choices and renders the final response using stored course details and templates. This is retrieval-grounded, constrained LLM assistance. It does not display unrestricted generated course facts. A running model server alone is not proof of inference. Show llm_used true in a successful run and chat.

Sources: backend/ai/engine.py:178,281,515; .env.example; README.md.

## 12. The employee learning experience

EXPLAIN, about 30 seconds
The interface supports a learning loop. The employee completes their profile, enables analysis consent and starts discovery. They can inspect a course’s source, explanation, factors and prerequisite advice before saving it. The learning plan records saved, in-progress and completed states. Completion is self-reported. It adds the course skills to the profile and invalidates the old analysis so a new discovery can reflect the change. Saving is just a local planning action. The application does not buy courses or enroll employees.

Sources: frontend/src/SettingsPages.tsx; Dashboard.tsx; LearningPages.tsx; components.tsx; backend/api.py, learning-plan endpoints.

## 13. Live demonstration

DEMO, about 3 minutes
Switch to the local application. First show Nadun’s profile and point to consent. Explain that the example role is Data Analyst and the goal is Data Scientist. Click Find opportunities and wait for completion. Open Agent activity and point to all four completed steps, timings and local-model use. Open a recommendation and read one actual skill-gap reason. Explain that the score ranks relevance and that catalogue offers are sample data. Save the course, open Learning plan and mark it in progress. Open Learning trends and show a source snippet. Finally ask Scout which beginner course supports the career goal and inspect its catalogue sources and model-use label. Do not mark a course completed unless you intend to update the profile. A rehearsal should establish actual outputs rather than memorizing a fixed score.

Sources: docs/DEMO_AND_SUBMISSION.md; current frontend screens; user account context.

## 14. Technology and persistent data

EXPLAIN, about 30 seconds
React builds the interface and TypeScript provides frontend types. Python and FastAPI implement HTTP endpoints. SQLite stores data in a file, normally data/skillscout.db, so accounts remain after restarting. The schema stores users and profile JSON, sessions, courses, posts, runs, analyses, learning plans and notifications. SQLite handles local transactions and uses write-ahead logging. This is suitable for the prototype’s scale. The database is not encrypted at rest. Git ignores the database, local environment and model files, so another teammate’s clone has its own local accounts.

Sources: frontend/package.json; backend/db.py:35; backend/config.py:24; .gitignore.

## 15. Security and access control

EXPLAIN, about 40 seconds
Authentication asks who the user is. Authorization asks what they can access. Passwords use salted PBKDF2-HMAC-SHA256 hashing with 310,000 iterations. Session tokens are random and stored as hashes, and the browser receives an HttpOnly cookie. CSRF and origin checks protect authenticated writes. Role checks and user IDs restrict personal data. HR gets aggregate organization information and only administrators can ingest posts or courses. Agent services use an internal key. The current database contains an employee account only, so the main demo does not rely on old HR or admin credentials. Loopback binding supports local use. Do not claim enterprise deployment security.

Sources: backend/security.py; backend/api.py; backend/worker.py; docs/RESPONSIBLE_AI.md.

## 16. Responsible AI in the workflow

EXPLAIN, about 40 seconds
Responsible AI is visible in the workflow. The employee must consent before analysis. Recommendations explain professional relevance and show their sources. The app labels synthetic posts and demonstration course metadata. Excluding protected attributes is useful, but it does not prove fairness because catalogue coverage, language and role mappings can still be biased. The user can export data or delete their account after password confirmation. Consent withdrawal clears current analysis and notifications, while historical private run records remain until account deletion. External database backups are outside that deletion. The system supports learning and does not make promotion, hiring or termination decisions.

Sources: backend/api.py, consent/export/deletion endpoints; docs/RESPONSIBLE_AI.md; user-provided responsible-AI scope.

## 17. Evaluation evidence

EXPLAIN, about 45 seconds
We reran the current Python suite and all 53 tests passed, with two third-party deprecation warnings. Retrieval evaluation uses seven author-labelled development queries and 32 demonstration courses. Precision at five measures the share of the five requested slots that contain relevant results, averaged over queries. Recall at five measures how many labelled relevant items appear in those results. MRR measures how early the first relevant item appears. NDCG rewards placing relevant items higher. MRR 1 means the first result was relevant for every query in this small set. It is not 100% real-world accuracy. The separate pre-viva checklist records a current frontend build error and the need to recheck live LLM inference.

Sources: Current outputs: .venv/bin/python -m pytest -q; .venv/bin/python -m backend.evaluation. backend/evaluation.py; tests/test_ai.py; tests/test_api.py.

## 18. Commercialization concept

EXPLAIN, about 40 seconds
The buyer would usually be an organization’s HR or learning and development department, while employees are the end users. The proposed pricing is per active employee per month. Starter is an assumption of LKR 300, Professional LKR 550, and Enterprise from LKR 800 with negotiated needs. These figures are hypotheses, not validated market prices. The original proposal suggests LKR 300 to 800 and negotiated enterprise pricing. Customer interviews, costs and willingness-to-pay tests would be needed before launching. Potential value includes more relevant learning discovery and less manual curation. The local prototype does not implement billing or tenant isolation.

Sources: User-supplied commercialization plan; frontend/src/SettingsPages.tsx, proposed plan copy; README.md, future commercialization scope.

## 19. Current scope and future development

EXPLAIN, about 35 seconds
The prototype already supports the personal learning workflow, grounded model assistance, in-app notifications and opt-in periodic analysis. By default the scheduler checks every 60 minutes while the gateway is running, and only for eligible consenting employees who enabled notifications. It searches stored data. It does not discover new web content by itself. The main limitations are the small synthetic corpus, curated role taxonomy, heuristic weights and development-only evaluation. Future work should begin with verified ingestion and independent evaluation, followed by enterprise integration and deployment controls.

Sources: backend/api.py, scheduler_tick; backend/config.py:36; README.md; docs/ARCHITECTURE.md.

## 20. SkillScout AI: discussion

CLOSE, about 20 seconds
SkillScout demonstrates how specialized services can turn an employee’s profile into explained training recommendations. The profile agent identifies needs, the trend agent supplies evidence, the retrieval agent finds candidates and the recommendation agent ranks them. The employee keeps the final choice. We are ready to demonstrate the code or discuss the design decisions.

Slides 21 to 30 are backup material for questions. You do not need to present all of them during the main talk.

Sources: Current codebase and user-confirmed GitHub repository URL.

## 21. Code map for the four agents

BACKUP ANSWER
Open backend/config.py to show AGENTS and ports. Open scripts/dev.py to show separate workers starting with different AGENT_KIND values. Open backend/worker.py to show POST /execute, authentication and the handler mapping. Then open backend/ai/engine.py at the relevant function. For retrieval, also show HybridIndex at line 222. Finally open backend/api.py and find _execute_pipeline to explain handoffs, result persistence and traces. Lines reflect the code reviewed on 21 September 2026 and can move after edits.

A good explanation is: here is the input, here is the decision, and here is the output. Avoid reading every line aloud.

Sources: backend/config.py:14; scripts/dev.py; backend/worker.py:87; backend/ai/engine.py:222,281,330,385,440; backend/api.py.

## 22. Why the skills are hardcoded

BACKUP ANSWER
A taxonomy is an organized vocabulary. For example, a role alias helps treat software developer and software engineer consistently. These mappings support repeatable, explainable gap extraction and give the language model a bounded list. The taxonomy does not contain all real-world skills or roles, and it is not automatically up to date. That is a limitation to acknowledge. The course catalogue is separate in backend/data/seed.py and SQLite. A production version could maintain role mappings in a curated database with provenance and review, while adding broader extraction models and coverage tests. Unknown roles may get weaker personalization under the current fallback.

Sources: backend/ai/taxonomy.py, SKILL_ALIASES, ROLE_SKILLS, ROLE_ALIASES, PREREQUISITES; backend/ai/engine.py:281.

## 23. Retrieval scoring in detail

BACKUP ANSWER
The BM25 implementation uses k1=1.5 and b=0.75. k1 controls how quickly additional occurrences of the same term stop adding much value. b controls document-length normalization. TF-IDF gives more weight to terms that help distinguish documents. Cosine compares the direction of the query and document vectors. The code min-max normalizes BM25 and cosine across the catalogue before the 62/38 blend. The second stage combines 88% hybrid relevance with 12% matched-course-skill coverage. This retrieval score chooses candidates. The recommendation agent then computes a separate personalized score from five factors. The weights are design choices rather than learned optimal values.

Sources: backend/ai/engine.py:222,242,257,266,385; constants at top of engine.py.

## 24. A worked recommendation score

BACKUP ANSWER
Multiply each factor score by its weight and add the contributions. Here that is 23 plus 23.5 plus 27 plus 13.2 plus 4.5, giving 91.2. These factor values are a teaching example, not the measured result for Nadun’s course. A high score means relatively good fit under our rules. It does not mean a 91.2% chance of completing the course or becoming a data scientist. The model does not choose these weights.

Sources: backend/ai/engine.py:436,440. The factor inputs are illustrative values adapted from the user’s project example, not measured recommendations.

## 25. HTTP communication and failure handling

BACKUP ANSWER
HTTP is the transport, REST-style endpoints define the operations, and JSON carries structured data. POST /execute receives an envelope containing run_id, user_id and the agent-specific payload. The worker checks the internal X-Agent-Key, validates the contract and calls its handler. The gateway verifies run identity when accepting results and records completed or failed steps. If a worker fails, the trace exposes which step failed rather than presenting an invented successful result. A model fallback is a different condition: the service may still finish successfully using deterministic logic, while disclosing llm_used false. The abbreviated JSON is explanatory and should not be pasted as a real complete request.

Sources: backend/worker.py:87; backend/api.py, call_agent and _execute_pipeline; CONTRACT.md.

## 26. Hallucination and grounded answers

BACKUP ANSWER
A language model might confidently invent a course, certification, price or discount. That is hallucination. SkillScout reduces this risk by retrieving catalogue entries first and restricting the model’s choices. Ask Scout asks for course IDs that must belong to the retrieved candidates. The application validates the JSON and uses templates plus stored course fields to render the answer. Invalid output falls back to deterministic selection with visible mode disclosure. This reduces the opportunity to invent facts, but source data can still be wrong, synthetic or stale. That is why the demonstration labels and provider checks remain important.

Sources: backend/ai/engine.py:178,211,281,515; README.md, provenance.

## 27. Running the project locally

BACKUP ANSWER
Open the entire project folder, not just a Python file. On the already configured Mac run python3 scripts/dev.py. It starts the gateway and four workers, starts the frontend, and handles the local model server when available. Open 127.0.0.1:5173 and keep the terminal running. For a fresh checkout, run setup and the model pull first. The README specifies Python 3.12 or later and Node 22.12 or later, plus Ollama. Use python instead of python3 on Windows where appropriate. If a port is in use, stop the previous launcher with Ctrl+C rather than launching another copy. Do not confuse a port number with a process ID.

Sources: README.md; scripts/setup.py; scripts/model.py; scripts/dev.py.

## 28. Pre-viva rehearsal checks

PRESENTER PREPARATION
The current npm build stops at frontend/src/main.tsx line 5 because an @ts-expect-error directive is unused. Remove that obsolete directive and its now-inaccurate explanatory comment after checking the file, then rerun npm --prefix frontend run build. This presentation task did not modify application code. The regression tests and retrieval evaluation were rerun successfully on 21 September 2026. Documentation records a successful live HTTP and local-model smoke test on 16 September, but that historical result does not establish present model availability. Before the viva, start the full stack, rehearse the employee journey and verify model use. Group members should prepare honest descriptions of what they personally built, adapted, tested and understood.

Sources: Current build output: TS2578, frontend/src/main.tsx:5. docs/VALIDATION.md. Group Assignment Brief.pdf, individual contribution criterion.

## 29. Likely viva questions

BACKUP ANSWERS
Four agents separate responsibilities and expose intermediate results, but the architectural trade-off is extra service and orchestration overhead. Describe them as specialized services in a bounded agent workflow, not four independent autonomous LLM planners. Our retrieval-grounded chat constrains course choices and renders validated facts, so be precise when using the term RAG. Scheduled checks add limited proactivity while the gateway runs. For personal contribution, do not memorize an invented division of work. Each presenter should point to real commits, files or tests and explain their decisions. If asked whether 100% can be guaranteed, explain that grades depend on meeting the rubric and demonstrating genuine understanding.

Sources: backend/config.py; backend/worker.py; backend/ai/engine.py; Group Assignment Brief.pdf, viva criteria.

## 30. Assignment coverage and references

REFERENCE NOTES
The supplied assignment is IT3041 Information Retrieval and Web Analytics, Design and Implementation of an Agentic AI System Integrating LLMs, NLP, Security, and Information Retrieval. The brief asks for at least two interacting agents, LLM use, NLP, IR, security, defined communication, Responsible AI and commercialization. Its viva criteria cover technical depth, individual contribution, communication protocols, Responsible AI and pricing. This system uses four agent services. The deck supports the viva but does not replace the separate report, GitHub deliverable or 3–5 minute Gen AI-based video.

Primary files: Group Assignment Brief.pdf; README.md; CONTRACT.md; backend/ai/engine.py; backend/ai/taxonomy.py; backend/config.py; backend/worker.py; backend/api.py; backend/db.py; backend/security.py; backend/evaluation.py; frontend/src; docs/ARCHITECTURE.md; docs/RESPONSIBLE_AI.md; docs/VALIDATION.md. GitHub: https://github.com/CheNivain/Skillscout-AI. No independent external market research is claimed.