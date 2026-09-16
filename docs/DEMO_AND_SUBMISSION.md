# Demonstration and final-submission guide

## Four-minute walkthrough

| Time | Screen / action | Explain |
|---|---|---|
| 0:00–0:30 | Login and Overview | Employees manually search professional feeds and course platforms. SkillScout personalizes that discovery. |
| 0:30–1:00 | Alex's Profile | Data Analyst with SQL, Excel, Power BI; goal Data Scientist; show consent, time and budget. |
| 1:00–1:45 | Find opportunities, Agent activity | Show all four independent HTTP services and completed step timings. Verify profile output says local model used. |
| 1:45–2:20 | Recommendations and details | Explain Python/statistics gaps, source catalogue, score factors and an explicitly labelled sample discount. |
| 2:20–2:50 | Courses, save, Learning plan | Search a skill, save a course, mark in progress. Human chooses whether to pursue training. |
| 2:50–3:20 | Trends and Ask Scout | Show evidence from the synthetic corpus, local grounded answer and cited course records. |
| 3:20–3:45 | Organization as HR | Aggregate learning metrics and B2B pricing assumptions; private profiles remain protected. |
| 3:45–4:00 | Profile privacy / conclusion | Summarize consent, explanations, export/deletion and scope of the prototype. |

Record with your own narration or the required generative-video tool. Do not label synthetic offers as real current promotions. If the model is unavailable, fix setup before recording the LLM requirement. The first model load may take time; perform a rehearsal before capture.

## Requirement mapping

| Assignment item | Demonstrable implementation |
|---|---|
| Selected domain/problem | Employee training and personalized opportunity discovery |
| Interacting agents | Four independently launched FastAPI worker processes |
| LLM | Local Ollama structured planning and grounded assistant |
| NLP | Skill/entity extraction, aliases, topic co-occurrence and evidence |
| IR | BM25 + TF-IDF cosine retrieval and reproducible labelled metrics |
| Security | Authentication, CSRF, authorization, private data scoping, worker key |
| Communication | HTTP/REST with run IDs, typed inputs and recorded handoff results |
| Responsible AI | Consent, transparent demo provenance, explanations, privacy controls, human control |
| Commercialization | B2B HR/L&D SaaS, per-employee pricing assumptions, enterprise roadmap |

## Still required from your group

The working software and supporting documentation do not replace your assessed group deliverables:

1. Transfer the actual design, methods and measured results into the lecturer's final report template. That template was not supplied here.
2. Add real contributor names, student IDs and truthful contribution records.
3. Record the required **3–5 minute Gen AI-based video** and include the local-model proof.
4. Upload the source repository to your own GitHub account. Exclude `.env`, `.local`, `.venv`, `data`, model weights and `node_modules`.
5. Reproduce setup on a fresh checkout, rerun evaluation, and record hardware/model settings and date alongside results.
6. Ensure every member can explain the code and demonstrate their contribution during the viva.

## Viva prompts

- Why are there four agents? Explain the separated objectives, decisions and input/output contracts.
- How are they coordinated? The gateway calls separate processes using authenticated HTTP/JSON; it checks run identity and records state.
- Which part is LLM-based and which part is deterministic? Inspect `llm_used`; explain bounded structured model choices and verified rendering.
- What is NLP here? Dictionary entity extraction and co-occurrence, with explicit limitations versus trained NER.
- Why hybrid IR? BM25 captures term relevance and length normalization; TF-IDF cosine compares term-weight direction. Neither is a dense semantic embedding.
- How do you handle hallucination? Validate selected skills/course IDs and render facts from retrieved records; reject invalid output and disclose fallback.
- How do you handle stale offers and data? Persisted expiry dates and comparative corpus windows, with source/demo labels.
- Does excluding sensitive fields ensure fairness? No; catalogue/taxonomy coverage and indirect proxies still require evaluation.
- What would enterprise rollout require? Verified data ingestion, model-license review, tenant isolation, SSO, TLS, encryption and audited integrations.
