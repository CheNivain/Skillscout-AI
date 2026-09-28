# SkillScout AI — Viva Rehearsal Guide

**C.N Wijesekara — IT23542006**  
**K.N. Weerakkody — IT23607200**  
Prepared 21 September 2026. Use this guide alongside the presentation and actual application.

Your goal is to explain the problem, demonstrate working behavior, and defend your design honestly. A presentation cannot guarantee a mark; understanding and evidence matter.

## Fix and rehearse before the viva

**The latest frontend production build failed. Resolve this before claiming the build passes.**

- [ ] In `frontend/src/main.tsx`, remove the obsolete `// @ts-expect-error...` directive at line 5 **and its preceding inaccurate comment** at line 4. Keep `import './styles.css';`. TypeScript reports TS2578 because that expected error no longer occurs. This guide does not change the code.
- [ ] Run `npm --prefix frontend run build` again and keep the successful output. Investigate any remaining error; do not assume success.
- [ ] Start the app, complete a full rehearsal, and verify four completed agent steps.
- [ ] Expand the profile step and check `llm_used: true`. Also rehearse a successful local-model Ask Scout answer. Availability alone does not prove inference.
- [ ] Check current offers and trends: stored timestamps age. Never promise a particular discount or ranking before checking it.
- [ ] Add truthful contribution evidence: commits, decisions, code each member understands, and work each actually performed. Do not invent responsibilities.

Latest rerun: **53 Python tests passed**. Seven development queries produced P@5 **0.657**, Recall@5 **0.833**, MRR **1.000**, NDCG@5 **0.885**. These measure small-catalogue retrieval, not “88.5% accurate recommendations.” The successful real-HTTP/LLM smoke record is dated **16 September**, and was not rerun today.

## Start locally

Open the entire project folder in VS Code. Select **Terminal → New Terminal** and run:

```bash
python3 scripts/dev.py
```

Open **http://127.0.0.1:5173** and keep the terminal running. Stop it with **Ctrl+C**. If a port is occupied, first stop the previous launcher rather than starting another copy.

For a fresh clone, run these separately before starting:

```bash
python3 scripts/setup.py
python3 scripts/model.py --pull
```

The launcher starts the gateway, four workers, frontend and available local Ollama. First model loading can be slower. Current data lives in `data/skillscout.db`; it contains 32 courses, 42 posts and one employee account. There are no current HR/admin accounts to use in this demo.

## A roughly 15-minute presentation

| Time | Explain/show |
|---|---|
| 0–2 minutes | Problem, target employee, proposed solution and example career goal. |
| 2–4 minutes | Architecture: browser, gateway, four workers, SQLite and Ollama. |
| 4–8 minutes | Each agent's input, decision and output; retrieval, scoring and grounding. |
| 8–12 minutes | Live demo below; describe the result as it appears. |
| 12–14 minutes | Validation, privacy, limitations and commercialization. |
| 14–15 minutes | Main takeaway and transition to questions/code. |

The deck has 20 main slides and 10 backup slides. Keep most slides to 20–35 seconds; reserve time for the demo. Use backup slides when asked rather than reading everything.

Opening line: **“SkillScout AI helps IT employees decide what to learn next by combining their professional profile, learning-content signals and a course catalogue through four specialized agents.”**

## Exact demo sequence with Nadun

1. **Sign in** using Nadun's existing credentials. Say: “This is an employee's private learning workspace.” Do not display the password.
2. Click **Profile & settings**. Review Nadun's existing data. For the rehearsed example, enter current role **Data Analyst**, goal **Data Scientist**, skills **SQL, Excel, Power BI**, experience **3**, weekly hours **6**, budget **80 USD**. Leave interests and biography empty for the exact five-gap example in the deck. Explain these are demonstration inputs.
3. Enable **Allow personalized learning analysis**. Enable **Proactive opportunity notifications** if demonstrating alerts. Click **Save profile & preferences**. Explain consent and professional-data use.
4. Click **Overview → Find opportunities**. Say: “The gateway starts the four-agent workflow.” Wait for completion; do not promise exact scores beforehand.
5. Click **Agent activity**. Show four services, their ports and the completed run. Expand **Inspect agent payload** for the profile step. Point to gaps and `llm_used`. The page shows actual execution records with summarized inputs/outputs.
6. Return to **Overview** and click a recommended course title. Show **Why this fits you**, matched skills, five factor scores, prerequisite advice and provider source. Say: “The score explains our ranking; it is not a probability of success.” Prices and discounts are labelled samples.
7. Close the details and click the course's **bookmark** to save it. Click **Learning plan**, then change its status dropdown to **In progress**. Saving is not enrollment or purchase.
8. Click **Courses**, search **Python**, and try the level/free filters. Explain that search retrieves stored catalogue records.
9. Click **Learning trends**, select a topic and show its evidence. Say: “These statistics describe our synthetic corpus over two adjacent 14-day windows.” They are not live LinkedIn activity.
10. Open **Ask Scout**, type **“Which beginner Python course fits my goal?”**, and send it. Show retrieved sources and the answer's model-use information. If fallback appears, explain it honestly.
11. Open the **bell** to show notifications if any qualify. No notice is valid behavior when no recommendation meets the threshold. Finish with profile privacy/export controls; explain deletion without deleting the account.

Optional feedback demo: mark a course **Completed**, explaining that progress is self-reported. This adds its skills/history, invalidates old recommendations and requires another discovery run. Do this last because it changes your example profile.

## Twelve likely viva questions

**1. What did you build?**  
A local employee-training assistant with a React interface, Python APIs, four specialized workers, SQLite persistence and local Ollama inference.

**2. Why four agents?**  
They separate four decisions: what the employee needs, what the supplied content discusses, which courses match, and which opportunities deserve priority. This makes handoffs testable and understandable.

**3. How do they communicate?**  
The gateway calls separate worker processes over authenticated HTTP/JSON. It passes one result into the next request and records status/timing. Workers do not directly call each other.

**4. Is every agent an LLM?**  
No. It is a bounded hybrid workflow. Ollama supports validated profile priority selection and grounded chat; extraction, retrieval and scoring use deterministic methods.

**5. Why hardcoded skills?**  
The taxonomy standardizes aliases and supplies role targets/prerequisites. It improves consistency but limits coverage. It needs maintenance and broader evidence for real deployment.

**6. Where is NLP?**  
Skill/entity extraction, alias matching and topic co-occurrence in learning text. It is dictionary-based NLP, not a trained transformer NER model.

**7. Where is information retrieval/RAG?**  
Course search combines BM25 and TF-IDF cosine lexical signals, with skill coverage. Ask Scout retrieves catalogue records before validated model selection and source-grounded rendering. There is no dense vector database.

**8. What is hallucination, and how is it reduced?**  
An AI can confidently invent facts. We constrain skills/course IDs, validate outputs and render course facts from stored records. Invalid responses trigger visible fallback; stored data can still be outdated.

**9. How are recommendations scored?**  
Profile relevance 25%, career alignment 25%, skill-gap relevance 30%, trend relevance 15%, discount value 5%. Suitability considers prerequisites/time/budget. These are explainable project heuristics.

**10. Is the system proactive?**  
Opted-in employees receive scheduled discovery while the gateway runs, normally every 60 minutes. The notice filter requires high priority and a score of at least 75. Since high priority starts at 78, the effective threshold is 78 under current scoring. Notices are deduplicated. There is no cloud task after shutdown.

**11. How is employee data protected?**  
Salted password hashes, protected sessions, CSRF checks, role checks, private user scoping and consent. HR sees aggregates. SQLite is not encrypted; local HTTP is not TLS. Enterprise security needs more work.

**12. What do your evaluation results prove?**  
Tests verify specified behavior, and seven manually labelled development queries evaluate retrieval on 32 demo courses. They do not establish real-world recommendation accuracy or unbiased employee outcomes.

## Code walkthrough map

Open these in VS Code; use **Go to Symbol** to find functions:

| File | What to point at |
|---|---|
| `backend/config.py` | `AGENTS`, ports and validated data contracts. |
| `scripts/dev.py` | Launching independent worker processes. |
| `backend/worker.py` | `/execute`, worker-key check and handler dispatch. |
| `backend/ai/engine.py` | `analyze_profile`, `discover_trends`, `retrieve_courses`, `recommend`, `answer_question`. |
| `backend/ai/taxonomy.py` | Skill aliases, role targets and prerequisites. |
| `backend/api.py` | `_execute_pipeline`, `scheduler_tick`, authentication and permissions. |
| `backend/db.py` | SQLite tables, saving results and completion feedback. |
| `frontend/src/App.tsx` | `run()` sends the Find opportunities request. |
| `backend/evaluation.py`, `tests/` | Ranking metrics and regression coverage. |

## Use the slides confidently

Open the `.pptx` in PowerPoint. In editing view, show the **Notes** pane for the speaking script. For presenting, choose **Slide Show** and enable **Presenter View** where available. With an external display, confirm the audience sees slides while you see notes/current-next slides. Menu names vary by version.

Rehearse aloud twice. Explain each diagram in your own words, then practice answering without notes. If unsure, show the relevant code rather than guessing. Each member should prepare a truthful account of their own work and supporting evidence.
