# SkillScout AI — simple viva presentation

Slides 1–20: presentation. Slides 21–24: backup. Allow about 15 minutes including the demo. Definitions are on the slides themselves.

## 1. SkillScout AI

Good morning. Our project is SkillScout AI. It helps an employee identify missing skills and find relevant courses. We will explain the problem, show how the four agents work and demonstrate the system. Each member should describe their actual contribution when asked.

Source: Group Assignment Brief.pdf; presenter details in the supplied Canva deck.

## 2. The problem and our objective

For example, a beginner needs a different course from someone with several years of experience. Our project supports that choice. We have not measured real-world time savings or employee career outcomes.

Source: Project problem statement; README.md.

## 3. What the system takes in and gives back

Course titles and provider links are stored in the catalogue. Prices, ratings and discounts are demonstration data and must be checked with the provider. There is no live LinkedIn scraping in this implementation.

Source: backend/data/seed.py; README.md.

## 4. A simple example

This is an illustrative profile. The current role mapping produces these five gaps when the profile has no additional interests or biography. Changing the profile can change the result. Missing from the profile does not prove the person lacks the skill; the profile should be kept accurate.

Source: backend/ai/engine.py: analyze_profile; backend/ai/taxonomy.py: ROLE_SKILLS.

## 5. The main parts of the system

The browser connects to the gateway. The gateway reads the database and calls the four workers in order. Workers do not directly call one another. Ollama is used by selected features; it does not run all recommendation logic.

Source: scripts/dev.py; backend/api.py; backend/worker.py; backend/db.py.

## 6. How the four agents work together

The gateway passes each result into later steps and records the run. This is a fixed, bounded workflow. It is not four independent language models planning freely. The final agent ranks opportunities; the gateway saves results and creates eligible notifications.

Source: backend/api.py: _execute_pipeline; backend/worker.py: execute.

## 7. Agent 1: identify learning needs

The function is analyze_profile() in backend/ai/engine.py. It also considers certifications, training history, interests and biography. If Ollama works, it may choose and order up to five existing gaps. The code checks those choices. If not, rule-based priorities remain.

Source: backend/ai/engine.py: analyze_profile; backend/ai/taxonomy.py.

## 8. Why skills are written in the code

The current taxonomy contains 40 canonical skills and 15 role mappings. This knowledge was curated for the project. It is not discovered or learned automatically by Ollama. Adding a new role may require extending both mappings and course coverage.

Source: backend/ai/taxonomy.py: SKILL_ALIASES, ROLE_SKILLS, ROLE_ALIASES, PREREQUISITES.

## 9. Agent 2: find learning trends

discover_trends() uses dictionary matching, not a trained neural named-entity model. It counts a skill once per post and compares two time windows. These trends describe the supplied synthetic posts. They are not proof of real job-market demand.

Source: backend/ai/engine.py: discover_trends; backend/ai/taxonomy.py; backend/data/seed.py.

## 10. Agent 3: find relevant courses

The code is retrieve_courses() and HybridIndex in backend/ai/engine.py. This is lexical retrieval using BM25 and sparse TF-IDF vectors, not neural embeddings. It normally returns up to 12 candidates. The final course recommendation score is calculated later by agent four.

Source: backend/ai/engine.py: HybridIndex, retrieve_courses.

## 11. Agent 4: rank and explain the courses

recommend() calculates these factors with project-defined rules. It removes completed or irrelevant courses and may exclude advanced courses when foundations are missing. The gateway creates eligible in-app notifications for opted-in users. Ratings are not a scoring factor.

Source: backend/ai/engine.py: recommend; backend/api.py: notification creation.

## 12. Where Ollama is used

The configured default model is qwen2.5:3b. The model is optional. Trend extraction, course retrieval and recommendation scores are implemented with algorithms and rules. A running Ollama service is not proof that a request used the model; inspect llm_used in the response.

Source: backend/ai/engine.py; backend/config.py; scripts/model.py.

## 13. Ask Scout and hallucination control

answer_question() provides retrieval-grounded assistance. Our implementation constrains selections and uses templates for the final facts instead of trusting unrestricted model prose. This reduces made-up course details, but it does not make outdated or inaccurate source records correct.

Source: backend/ai/engine.py: answer_question; tests/test_ai.py.

## 14. How information is stored and protected

Passwords use PBKDF2-HMAC-SHA256 with a salt and 310,000 iterations. Session tokens are hashed in the database. Cookies are HttpOnly and SameSite. The local SQLite file is not encrypted. Production deployment would need further hardening, including HTTPS and stronger operational controls.

Source: backend/db.py; backend/security.py; backend/api.py; backend/worker.py.

## 15. Responsible use of employee data

Fairness is a design intention, not a proven fairness result. The small curated catalogue may favour supported roles and providers. Consent withdrawal removes current analyses and notices; prior private run history remains until account deletion. Externally saved backups are outside that deletion.

Source: docs/RESPONSIBLE_AI.md; backend/api.py.

## 16. Live demonstration

Use the existing employee account. For the exact example use Data Analyst, SQL/Excel/Power BI and Data Scientist, with no extra interests or biography. Explain that saving a course is a personal choice. If showing completion, it is self-reported and changes the profile; do not mark a course complete merely to test the button without intending to change that demo account.

Source: frontend/src; backend/api.py; project demo workflow.

## 17. Testing and evaluation

Recorded on 21 September 2026. Relevance labels were authored for development, not collected from an independent user study. NDCG@5 was 0.885. Automated tests do not prove production readiness. See the separate rehearsal notes for the known frontend build check and current model verification steps.

Source: tests/test_ai.py; tests/test_api.py; backend/evaluation.py; recorded validation outputs.

## 18. Limitations and future improvements

Scheduled checks only run while the local gateway is running. They re-analyse stored data; they are not a live internet monitoring service. Integration with HR systems, email and Teams is proposed future work.

Source: README.md; docs/ARCHITECTURE.md; backend/api.py: scheduled discovery.

## 19. Possible organizational use

This addresses the assignment’s commercialization requirement. Costs could include hosting, model inference, data maintenance, support and integrations. We have not validated willingness to pay or launched an enterprise service.

Source: User-supplied commercialization proposal; Group Assignment Brief.pdf.

## 20. What we implemented

Our project demonstrates a complete bounded workflow using the provided data. The employee remains in control. We can now show the code and answer questions about our design decisions. Do not claim unmeasured business results or invented personal contributions.

Source: README.md; backend/ai/engine.py; backend/api.py; frontend/src.

## 21. Code locations for the four agents

Open backend/ai/engine.py in VS Code and use Find to locate each named function. Open backend/worker.py to show AGENT_KIND dispatch and backend/api.py to show _execute_pipeline. Use function names because line numbers can change after edits.

Source: backend/ai/engine.py; backend/worker.py; backend/api.py; scripts/dev.py.

## 22. How the agents communicate

Profile, trends, retrieval and recommendation workers use ports 8101 to 8104. Each is a separate FastAPI process. A port is a numbered network endpoint. The gateway uses port 8000. The X-Agent-Key header is a shared secret for internal calls, not a user password.

Source: CONTRACT.md; backend/config.py; backend/worker.py; backend/api.py.

## 23. The two scoring stages

BM25 and cosine components are normalized before blending. Profile fit includes level, budget and time, with penalties where applicable. Notification creation also requires opt-in and deduplication; its high-priority check makes the effective score threshold 78. A discount is only one small factor.

Source: backend/ai/engine.py: HybridIndex, retrieve_courses, recommend; backend/api.py.

## 24. Common viva questions

Activate the installed virtual environment first if needed. If a port is busy, stop the existing project process before starting a second copy. The detailed original rehearsal guide contains startup and troubleshooting instructions. Primary references for this deck: assignment brief, README.md, CONTRACT.md, backend source and docs/ARCHITECTURE.md. Repository: https://github.com/CheNivain/Skillscout-AI.

Source: scripts/dev.py; README.md; backend source; Group Assignment Brief.pdf.