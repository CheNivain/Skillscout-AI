# Architecture and methodology

## Scope and inputs

SkillScout AI addresses course discovery for IT employees using a professional profile, a curated course catalogue and an explicitly supplied learning-content corpus. SQLite persists accounts, sessions, professional profiles, catalogues, agent runs, analyses, plans and notifications. The UI never needs a model key or worker secret.

## Agent contracts

Every worker accepts `POST /execute` with `X-Agent-Key` and an envelope:

```json
{"run_id":"uuid", "user_id":"uuid", "payload":{}}
```

It responds with `{"run_id":"uuid","agent":"profile","result":{}}`. Payload shape is specific to the agent. The gateway records each step and checks response identity and result validity. Services bind to `127.0.0.1`; they are not public endpoints.

| Agent | Input | Decision / method | Output |
|---|---|---|---|
| Profile & training needs | Professional profile | Canonical skill taxonomy, role targets, prerequisite ordering; validated local LLM priority selection | Current and target skills, gaps, priorities, model-use flag |
| Learning trend discovery | Posts and needs | Dictionary-based entity/keyphrase extraction, co-occurrence, current/prior 14-day mention counts | Ranked topics and original evidence |
| Training opportunity retrieval | Catalogue, needs, trends | BM25 and TF-IDF cosine, normalized weighted combination, skill overlap | Ranked candidates and matched skills |
| Recommendation & notification | Profile, needs, trends, candidates | Transparent relevance/career/gap/trend/value scores, prerequisite and budget considerations | Explained recommendations and threshold-triggered in-app notices |

The gateway relays outputs to the next worker. It also implements scheduling, authentication, authorization and persistence. The fourth agent decides scores and priorities; the gateway persists/deduplicates notices so the worker stays stateless.

## NLP and retrieval

Entity extraction uses a curated skill dictionary with aliases and word boundaries. This is dictionary-based NLP, not a trained NER transformer. Role matching is taxonomy-based, so unfamiliar roles may require explicit interests/skills and expanded taxonomy coverage. Training history contributes evidence of acquired skills.

Each course document combines title, description, category, kind, provider, level and skills. BM25 uses `k1=1.5` and `b=0.75`. TF-IDF cosine supplies a second lexical similarity signal. Normalized retrieval is `0.62 × BM25 + 0.38 × cosine`; skill coverage further influences candidate ranking. This is hybrid **lexical** retrieval, not a dense embedding/vector database. Explicit search queries drive relevance without being overwhelmed by profile keywords.

Trend statistics compare two adjacent 14-day windows. The seeded corpus is small and synthetic; mention changes do not measure real labor-market demand. A first appearance has a displayed +100% convention with an explanation because ordinary percentage growth from zero is undefined. Evidence excerpts link statistics back to input posts.

The final recommendation score uses five displayed factors: 25% profile relevance, 25% career alignment, 30% skill-gap relevance, 15% trend relevance and 5% discount value. These are project heuristics, not calibrated probabilities. Missing prerequisites and budget/time constraints affect suitability.

## Grounded local LLM decisions

Ollama performs actual inference through `/api/chat`. The profile agent requests a structured priority sequence and validates every selected skill against derived gaps. The assistant retrieves course documents before asking the model to choose grounded items; catalogue values and citations are rendered from stored data. Model output cannot directly overwrite course prices, URLs or scores. If the model is absent, times out or returns invalid structure, the system uses a deterministic result and reports `llm_used: false`.

The model influences bounded planning/selection. Deterministic templates render explanations from validated records. This design preserves evidence and prevents arbitrary generated course facts while satisfying the need for actual local LLM use. An LLM status indicator shows availability; per-run/per-answer metadata shows whether a valid model response was actually used.

## State and human feedback

A discovery run uses one profile version. If consent is withdrawn or the profile changes during inference, stale results are not committed. Saving a course does not enroll or purchase it. Completion updates local training history; a subsequent run can reconsider gaps. Users decide whether to follow a provider link or undertake any course.

The scheduler runs only while the gateway is running and only for eligible opted-in employees. This is local proactive discovery over stored data; it cannot discover web offers absent from the catalogue. There is no background cloud task after the app exits.

## Evaluation

Run `python -m backend.evaluation` within the project environment. It reports precision@5, recall@5, reciprocal rank and NDCG@5 on a small labelled catalogue query set. The benchmark measures retrieval, not LLM generation, employee outcomes or general web search quality. Query labels are manually curated for this assignment and should be extended with independent judgements and real, consented data for research claims.

API tests isolate SQLite databases and cover security and state transitions. The live smoke script checks genuine service-to-service HTTP communication and can require successful Ollama inference. The build typechecks the UI. Browser checks cover visible navigation and core user interactions. See `docs/VALIDATION.md` for the actual final verification record.
