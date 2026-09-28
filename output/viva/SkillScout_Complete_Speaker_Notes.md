# SkillScout AI — system and individual assessments

Slides 1–19: system presentation. Slides 20–26: Assignment 2 assessment plans. Slide 27: conclusion. Slides 28–31: backup. Allow about 18–22 minutes including the demo, or select the relevant individual section for a shorter viva. Definitions are on the slides themselves.

Important: all 60 cases in the four supplied individual reports are NOT RUN. No new independent attack results are claimed.

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

## 20. Assignment 2: individual assessments

Assignment 2 assesses the same system from four individual perspectives. These slides describe the supplied plans and risk hypotheses. They are not completed empirical assessment results. The earlier Python tests and retrieval metrics are separate project validation and do not replace the 15 independent tests required from each student.

Source: Individual Assignment Brief.pdf, pp. 1–5; all four Assignment 2 reports, document status and section 5.

## 21. The planned testing method

Record the code revision, date, test user, consent state, model configuration and llm_used flag. Report PASS, FAIL, INCONCLUSIVE or NOT RUN accurately. A fallback run does not prove that the language model resisted an attack. Remove secrets from screenshots and logs. Reset test data after each case. These are proposed methods from the reports, not claims of execution.

Source: Individual Assignment Brief.pdf, pp. 3–5; all four reports, section 3.

## 22. Chelaka: Responsible AI and bias

The report plans 15 cases on hallucination, sample prices, expired offers, unsupported professions, skill aliases, language, budget, experience, stale trends, synthetic corpus skew, repeated terms, discounts, explanations, harmful employment decisions and model failure transparency. Selected TC-01, TC-06 and TC-12 have preliminary Medium impact and Possible likelihood estimates. These are hypotheses, not confirmed severity ratings. Excluding protected personal characteristics alone does not prove fairness. Compare otherwise equivalent inputs and preserve the actual outputs.

Source: Chelaka_Assignment_2_Responsible_AI_and_Bias_Assessment.docx, TC-01, TC-06, TC-12 and preliminary register.

## 23. Dinadi: prompt attacks

The report plans 15 cases: profile-bio instruction override, role-field instructions, course-description injection, post injection, prompt extraction, role-play jailbreak, repeated-turn persistence, JSON escape, Unicode disguise, language switching, fake authority, disguised tool output, secret requests, repeated attacks and fallback comparison. TC-03 and TC-06 have preliminary High impact/Possible likelihood; TC-08 has Medium impact/Possible likelihood. Do not describe attacks as blocked or successful until independently run. Check whether untrusted text actually reaches the model. Output validation and server permissions are the intended boundaries.

Source: Dinadi_Assignment_2_Prompt_Injection_and_Jailbreak_Analysis.docx, TC-03, TC-06, TC-08 and preliminary register.

## 24. Nadun: privacy and data leakage

The report plans 15 cases on another employee’s records, employee access to HR/admin APIs, anonymous access, sessions after logout/deletion, CSRF, exports, consent before/during runs, password storage, unencrypted database files, demo credentials if enabled, logs and alternate model endpoints. TC-01 and TC-08 have preliminary High impact/Possible likelihood. TC-12 has High impact/Likely with filesystem access. SQLite’s lack of encryption is a documented design limitation; the supplied report has not independently executed its case. Password hashing does not encrypt the rest of the database.

Source: Nadun_Assignment_2_Privacy_and_Data_Leakage_Assessment.docx, TC-01, TC-08, TC-12; backend/db.py.

## 25. Sanali: retrieval and security

The report plans 15 cases: exact-term relevance, no-match query, BM25 length manipulation, keyword stuffing, source URLs, forged course IDs, missing/wrong worker keys, run ID substitution, agent kind substitution, employee admin access, query injection, stale offers, poisoned descriptions and metric reproduction. TC-04 has preliminary Medium impact/Possible likelihood. TC-09 and TC-14 have High impact/Possible likelihood. An authenticated record can still contain wrong information: checking source facts remains necessary. Existing development metrics are not new independent test evidence.

Source: Sanali_Assignment_2_Information_Retrieval_and_Security_Assessment.docx, TC-04, TC-09, TC-14 and preliminary register.

## 26. How risk will be judged

No final severity ratings are justified by the supplied NOT RUN cases. An example hypothesis is cross-user data access: impact could be High if sensitive data were exposed, but access conditions, affected users and reproduction must be established before classifying a real finding. Proposed controls include strict output checks, server permissions, source review, data minimization and protection of stored files. Each student must explain why a test succeeded or failed using their own evidence. The brief gives conflicting mark splits on pages 4 and 6; confirm that separately with the lecturer.

Source: Individual Assignment Brief.pdf, pp. 3–6; all four reports, sections 6–7.

## 27. What we implemented

Our project demonstrates a complete bounded workflow using the provided data. The employee remains in control. We can now show the code and answer questions about our design decisions. Do not claim unmeasured business results or invented personal contributions.

Source: README.md; backend/ai/engine.py; backend/api.py; frontend/src.

## 28. Code locations for the four agents

Open backend/ai/engine.py in VS Code and use Find to locate each named function. Open backend/worker.py to show AGENT_KIND dispatch and backend/api.py to show _execute_pipeline. Use function names because line numbers can change after edits.

Source: backend/ai/engine.py; backend/worker.py; backend/api.py; scripts/dev.py.

## 29. How the agents communicate

Profile, trends, retrieval and recommendation workers use ports 8101 to 8104. Each is a separate FastAPI process. A port is a numbered network endpoint. The gateway uses port 8000. The X-Agent-Key header is a shared secret for internal calls, not a user password.

Source: CONTRACT.md; backend/config.py; backend/worker.py; backend/api.py.

## 30. The two scoring stages

BM25 and cosine components are normalized before blending. Profile fit includes level, budget and time, with penalties where applicable. Notification creation also requires opt-in and deduplication; its high-priority check makes the effective score threshold 78. A discount is only one small factor.

Source: backend/ai/engine.py: HybridIndex, retrieve_courses, recommend; backend/api.py.

## 31. Common viva questions

Activate the installed virtual environment first if needed. If a port is busy, stop the existing project process before starting a second copy. The detailed original rehearsal guide contains startup and troubleshooting instructions. Primary references for this deck: assignment brief, README.md, CONTRACT.md, backend source and docs/ARCHITECTURE.md. Repository: https://github.com/CheNivain/Skillscout-AI.

Source: scripts/dev.py; README.md; backend source; Group Assignment Brief.pdf.