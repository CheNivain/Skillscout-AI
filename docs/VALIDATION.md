# Local validation

Validated on 16 September 2026 on this macOS workspace. These results describe the local prototype, not a production security certification or independent research benchmark.

| Check | Result |
|---|---|
| Python regression suite | 53 tests passed; two third-party deprecation warnings |
| TypeScript and Vite production build | Passed |
| Real HTTP end-to-end smoke check | Passed against the gateway and all four independent agent services |
| Local model inference | `qwen2.5:3b` through Ollama; profile and grounded chat both reported `llm_used: true` |
| Final smoke duration | 2.81 seconds with the model already warm; cold starts take longer |
| Retrieval development evaluation | Precision@5 0.657, Recall@5 0.833, MRR 1.000, NDCG@5 0.885 |

The HTTP smoke check creates a temporary employee, verifies consent enforcement, completes all four agents, retrieves ten recommendations, saves/starts/completes a course, tests search and grounded chat, checks role restrictions and private export, then deletes the temporary account and verifies its session is invalidated.

Regression coverage includes authentication and authorization, cross-user isolation, CSRF and origin checks, bounded inputs, agent handoff/run identity, consent and profile changes during runs, failed-worker traces, notification deduplication, offer expiry, prerequisite guidance, retrieval quality, and validated model output/fallback.

Browser checks exercised employee login, discovery, course search/details, saved-course progress, chat with catalogue sources, trend evidence, profile settings, admin analytics and ingestion forms. The responsive layout was inspected at desktop and phone widths. The final simplification removes decorative banners and promotional copy, with plain navigation and a compact overview.

The retrieval evaluation uses seven small, author-labelled development queries over the bundled demonstration catalogue. It is reproducible with `python -m backend.evaluation`, but is not a held-out benchmark and does not establish real-world recommendation accuracy. Prices, discounts, ratings and learning posts are labelled demonstration data. No live course-platform or LinkedIn integration was tested or claimed.

See the root README for repeatable test/build/smoke commands. Windows launch paths are implemented but have not been independently exercised. No fresh-machine installation, external deployment, GitHub upload or enterprise integration is claimed by this validation.
