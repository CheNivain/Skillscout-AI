# Security, privacy and Responsible AI

## Implemented controls

- Password hashing with a salted password derivation function; no plaintext passwords in the database.
- Random session tokens stored as hashes; HttpOnly, SameSite cookies; CSRF protection on authenticated writes.
- Server-side employee/HR/admin checks. Employees access their own records; HR views aggregates rather than individual private career profiles.
- Authenticated worker HTTP endpoints, bounded requests and validated input fields, secure URL validation for source records.
- Rate limits for sensitive endpoints and loopback network binding.
- Explicit consent for analysis and personalized chat; opt-in in-app scheduled recommendations.
- Profile-version checks prevent saving results after profile changes or consent withdrawal.
- Export of personal application data without password/session secrets; account deletion with password confirmation. The last admin cannot be deleted through the app.
- Professional fields drive recommendations. Protected personal characteristics are not scoring inputs.
- Visible factor scores, matched skills, source links, trace status, demo-data labels and actual model-use flags.
- User choice over courses. No automated hiring, firing, promotion or performance decisions.

## Limitations to explain in the viva

**Privacy:** SQLite is a local plaintext database with filesystem access restrictions. Loopback HTTP is suitable for the local demo; TLS and encryption at rest are not implemented. Do not enter confidential employee records on a shared computer. Local inference avoids sending profile prompts to a paid cloud API, but an administrator who changes the configured endpoint changes that data path. Database backups and OS-level copies are outside account deletion.

**Fairness:** Excluding protected attributes does not prove fairness. Role taxonomies, catalogue coverage, budget constraints and language may introduce bias. Sparse synthetic data cannot establish fairness across real employee groups. Review recommendations, broaden coverage, audit outcomes and collect consensual feedback before organizational use.

**Grounding:** Course facts come from local source records. Structured model outputs are validated against those records. This limits hallucinated course claims; it does not certify the records are current or remove all prompt-injection risks. Administrators must verify sources, label samples and maintain expiry dates. The app performs no automatic browsing or third-party purchases.

**Security:** Known demo credentials and local process-level rate limits are development conveniences. This is a single-organization academic prototype, without SSO, MFA, multi-tenant isolation, independent penetration testing, encrypted backups, an immutable audit log or deployment hardening. Those are explicit future requirements before exposing the service to untrusted networks.

**Data provenance:** Learning posts are synthetic and course metadata is sample material with provider references. No LinkedIn scraping or third-party personal employee data is used. Demo prices, ratings, discounts and durations are not live verified commercial claims.

**Model license:** The chosen Qwen 2.5 3B model carries a research license. Model licensing is separate from your application code; review both before a commercial deployment or choose a suitably licensed alternative. Framework/package licenses remain with their owners.

## Commercialization concept

Customer: organizations and HR/L&D departments. End users: employees. Proposed B2B SaaS pricing assumptions are LKR 300 (Starter), LKR 550 (Professional), and from LKR 800 (Enterprise) per active employee/month. These are hypothesis prices, not validated willingness-to-pay or financial forecasts.

Pilot with a small organization: consented employee profiles, approved provider catalogue, human-reviewed recommendations and measurable time saved. Measure recommendation acceptance, course completion and user-reported usefulness before expanding. Future enterprise work includes SSO, tenant isolation, audited HR/LMS connectors, Teams/email delivery, infrastructure monitoring, verified course feeds and retention policies. These integrations are a roadmap, not currently implemented features.
