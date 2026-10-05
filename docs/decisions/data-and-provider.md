# SellerOS Data, LLM Provider and Evaluation Policy

PLAN-06, 5 October 2026. Documentation only; no data generation, provider selection, API calls, credentials, application code or evaluation results. **APPROVED WORKING PROJECT RULE — DP-01:** the user selected synthetic-only demo and evaluation; real data requires separate approval. This selection is recorded from the user's reply in this chat, not inferred instructor approval.

## 1. Sources, scope and repository evidence

Sources: [PLAN-02 scope](../requirements/scope.md), [requirement register](../requirements/traceability.csv), [PLAN-03 rules](order-and-inventory.md), [PLAN-04 access policy](auth-and-store.md), and [PLAN-05 analytics decisions](analytics-and-ai.md). Read-only inspection found branch `docs`, clean tree, the prerequisite documents, two proposal/plan documents, and `check.py`. No application, evaluation dataset, provider configuration or dependency manifest exists. This inventory does not claim an exhaustive secret scan of machine/Git history.

Retain the approved React/Vite/TypeScript + Django/DRF/PostgreSQL architecture and analysis libraries. LLM access is backend-isolated. Owner and active staff may access their own store's AI/analytics under PLAN-04; staff cannot change store settings/user permissions. Customer and store authorization applies to retrieval, prompts, results, logs, caches and evaluation artifacts.

Approved existing constraints: synthetic or explicitly authorized data only; no unapproved real-customer processing, frontend provider secrets, automatic sending or autonomous business actions. Preserve all earlier open decisions. No formal accounting, tax advice, guaranteed forecast or business impact claims.

## 2. Approved demo and evaluation data policy

**APPROVED WORKING PROJECT RULE:** synthetic-only for the prototype demonstration and evaluation. Use fabricated seller accounts, products, stock, customers, orders, costs and messages; never transform a real customer export into a “synthetic” fixture without separate review. Dummy identifiers/contact fields must not route messages to real people. Do not collect real credentials, addresses, conversations, payment details or sensitive attributes.

Future DATA tasks should create deterministic fixture manifests with source type, generator/version/seed when applicable, date range, timezone/currency policy, store boundaries, intended cases and known limitations. Fixtures must obey approved lifecycle/snapshot rules or be explicitly labeled invalid-input test cases. Include two stores, owner/staff/revoked-user cases, empty/incomplete history, missing versus known-zero costs, repeated event requests, sparse/all-zero sales and supported scenario arithmetic. Unresolved thresholds/currency/lifecycle cases remain blocked rather than silently selected by fixture generation.

Synthetic series can prove workflow, arithmetic, data gates and evaluation pipeline behavior. They cannot establish representative seller forecast accuracy, business benefit, causal price elasticity, real-user usability or production performance. Any reported synthetic benchmark must be labeled synthetic, with generator and split; no benchmark is run in PLAN-06.

If real/authorized data is later proposed, require written purpose, provenance/permission, permitted fields/users, institutional review where applicable, minimization/redaction, provider-transfer approval, retention/deletion/backups, and isolated access before collection/import/use. Authorization alone does not settle privacy/provider transfer. Pseudonymized records remain potentially identifying; anonymization must not be assumed. This exception is not approved by this document.

## 3. LLM context minimization and secrets

Retrieve only authorized current-store facts needed for the task. Customer assistant receives a minimized message and relevant product/variant/price/stock facts, not the customer table, full conversation archive or another store's catalogue. Advisor receives computed period metrics and completeness metadata, not raw customer identities or bulk transaction exports. Profit/model arithmetic remains deterministic/backend-computed.

Before external transmission, remove unnecessary names, contacts, addresses, credentials, account IDs and payment information; free text requires review/redaction because it may contain identifiers or prompt-like instructions. Do not promise perfect automated redaction. If minimization cannot be assured or transfer approval is absent, no provider call. Synthetic data does not remove budget/provider-review gates.

Treat pasted messages and retrieved text as untrusted task content, never instructions authorizing tools, data disclosure or changes. No provider tool execution, URL-driven retrieval or write access is implied. Outputs stay reviewable suggestions; unknown facts trigger disclosure/clarification. Capture source facts/as-of metadata for evaluation without granting cross-store access.

Provider keys must be server-side secret configuration, excluded from Git, frontend bundles, prompts, logs, screenshots and evidence. Templates contain placeholders only. No key is requested, read, created or tested in this task. Future configuration must verify that public build variables never contain credentials and failures do not dump request headers/secrets. Rotation/revocation mechanics belong to later configuration, not invented implementation here.

## 4. Provider selection and privacy-review gate

**[DECISION REQUIRED] DP-02:** provider/model remains undecided. No named vendor is selected and no current terms/prices are asserted. At selection time obtain current official provider/model documentation and record dated links and review evidence; this task defines criteria rather than performing a vendor comparison.

| Review criterion | Evidence needed before approval | Reject/block condition |
| --- | --- | --- |
| Privacy and training use | Applicable API/product/account terms, input/output training treatment, opt-outs and exceptions | Unsupported assumptions about “no training” or terms incompatible with permitted data |
| Retention and deletion | Provider request/log retention, abuse/security exceptions, deletion options, regional/subprocessor controls | Unknown retention or required deletion not achievable |
| Transfer and authorization | Institution/team permission, permitted fields, purpose, geography where required | Unapproved transfer or unnecessary customer data |
| Key handling/access | Backend-only deployment and secret ownership/rotation plan | Browser-exposed/shared repository keys or unchecked operator access |
| Cost/availability | Model price units, currency, account limits, regional access and budget estimate | No approved budget or unsupported availability assumption |
| Output quality | Grounded reply/summary evaluation on representative permitted cases | Unverified claims, fabricated arithmetic or unacceptable critical failures |
| Reliability | Timeout, rate-limit/error behavior, bounded retry and fallback tests | Unbounded retries/costs or failure masquerading as success |
| Reproducibility | Model/version identifier and available generation settings captured | No record of configuration used for evaluation |

Reviewer/approval record must identify who approved, date, provider/API/model/version, applicable account options, source links, data categories, retention settings, approved limits and outstanding risks. Do not infer instructor review or legal compliance. No external provider is operationally enabled while this gate is incomplete.

## 5. Cost limits and service fallback

**APPROVED EXISTING BOUNDARY:** no billable provider use before provider, transfer and budget approval. For this planning stage there are zero authorized provider calls and no authorized spend; this is not a selected future monthly budget.

**[DECISION REQUIRED] DP-03:** approve budget amount/currency/time window, per-request input/output limits, daily/account/store usage quotas, model price basis, timeout, retry count/backoff and who may change limits. Candidate design uses a hard cap and per-request preflight allowance; numeric values are intentionally unselected. Include retry/failed-call charges and concurrent calls in the budget accounting. A provider dashboard alert alone is not proof of an enforced cap. Never assume free credits.

PLAN-05 fallback remains: disclose provider outage/unavailability, retain valid deterministic descriptive metrics, and do not fabricate a successful AI reply/insight. No automatic message send or provider-switching to unreviewed terms. **[DECISION REQUIRED] DP-05:** select whether a clearly labeled deterministic template draft/summary is allowed for demo. Until selected, no template is misrepresented as LLM output; service-unavailable state is sufficient. Request timeout/HTTP details remain later API contracts.

## 6. Retention, privacy and debugging evidence

FR-19 requires enough input evidence for debugging/evaluation, not indiscriminate prompt logging. Proposed minimal request evidence: store-authorized opaque request/case ID, task, timestamp/period, model/method/config version, relevant fact/metric snapshot or reproducible fixture reference, redaction/completeness indicators, outcome/error category, token/cost accounting when available, and rubric judgments. Exact schema is a later task. Do not log credentials or raw customer identifiers; no full production messages/prompts by default. Synthetic fixture cases may preserve sanitized inputs in approved evaluation evidence.

**[DECISION REQUIRED] DP-04:** approve local database/log/evaluation retention periods, deletion/reset workflow and authorized operator, backup retention/removal, provider-retention compatibility, and whether any minimized message/result content is stored. Candidates: fixture-only reproducible input references with minimal metadata, or short-lived minimized input/output evidence with explicit duration. Neither candidate duration/format is selected. Provider retention is separate from local deletion; deleting local data does not imply provider deletion.

Access follows PLAN-04 active membership; revocation blocks further seller-data access, including logs/results. Staff analytics access does not expose keys/other accounts or grant bulk account-management/reset rights. Demo reset/deletion authority and preserving required transaction/evaluation evidence need approval under AD-04/DP-04; do not create a destructive reset endpoint here. Real-data cases remain blocked even if later storage code exists, until approval gates are met.

## 7. Evaluation rubric and checklist

The rubric below records planned evaluation dimensions and candidate rating anchors. Numeric acceptance/sample-size decisions remain DP-06. No ratings, forecast accuracy or business improvements are claimed.

| Feature | Required input/reference | Evaluation dimensions and method | Planned evidence |
| --- | --- | --- | --- |
| Customer Assistant | Minimized case message, current-store retrieved facts, approved expected fact constraints | Relevance, factual consistency, groundedness, unsupported content, seller edit/discard controls; compare every price/stock claim with retrieval | Case record with facts, sanitized draft and dimension judgments |
| Business Advisor | Verified computed metrics, selected period and missing-data flags | Metric/period consistency, groundedness, usefulness, clear limits; no invented trends or arithmetic | Metric snapshot/fixture reference and summary review |
| Customer Segmentation | Approved behavior features/thresholds and hand-expected groups | Criteria consistency, boundary/overlap cases, interpretability; exclude sensitive traits | Feature/criteria versions and expected versus actual labels |
| Demand Forecasting | Eligible history, sufficiency policy, past-only split, baseline/method | Data-gate correctness, leakage checks, horizon identification, selected error metric and baseline comparison | Dataset/seed, split dates, configuration, actual observed scores or insufficient-data outcome |
| Profit Intelligence | Explicit revenue/discount/cost/delivery/expense fixtures | Deterministic hand arithmetic, missing-cost disclosure, once-only reversals, no arbitrary allocation | Inputs/formula/rounding version and expected versus observed values |
| What-if Simulator | Approved baseline/variables and assumptions | Hand calculation, bounds/completeness, estimate label and non-causal explanation; no production mutations | Baseline/scenario inputs, expected/observed output and assumptions |

Candidate text rating anchors: 0 = unsupported/incorrect or unusable; 1 = partly supported but incomplete/unclear; 2 = supported, relevant and clear. Assess each dimension separately and retain explanations; do not collapse grounding failures into a favorable average. An unavailable/decision-blocked feature is NOT EVALUATED, not a score of zero or a fabricated pass. Human reviewer and reviewed model output must be identified; self-scoring by the LLM is not independent evidence.

Critical conditions requiring repair/withheld success claims: cross-store disclosure, exposed secrets, unapproved data/provider transmission, unsupported price/availability presented as verified, fabricated metrics/results, unauthorized mutation/automatic sending, duplicate economic effects, or claimed complete profit with unknown required costs. These follow existing requirements; no numeric AI acceptance threshold is invented.

Evaluation run checklist (all pending):

- [ ] Dataset type/provenance and case manifest approved; real data excluded until separate approval.
- [ ] Relevant DR/AC business rules finalized; unresolved cases marked BLOCKED/NOT EVALUATED.
- [ ] Same-store owner/staff/revoked/foreign access fixtures included.
- [ ] Provider/privacy/budget gates passed for external calls, or explicit unavailable behavior evaluated.
- [ ] Minimized context, redaction, secret handling and untrusted-message boundaries verified.
- [ ] All six feature references/methods, expected outputs and negative cases recorded.
- [ ] Human rating criteria/sample plan agreed; critical failures reported separately.
- [ ] Forecast split/preprocessing uses past data only; baseline and candidate compared on identical periods.
- [ ] Deterministic profit/scenario cases match hand arithmetic with approved precision.
- [ ] Empty/incomplete/zero/outage states and disclosure presentation assessed.
- [ ] Commands, dataset/method/model versions, reviewer/date and observed outcomes recorded honestly.
- [ ] Local/provider retention/reset behavior documented and verified under approved authority.

**[DECISION REQUIRED] DP-06:** sample size/case mix, human reviewer(s), repetitions, numeric text acceptance criteria and any forecast error target. Preserve PLAN-05 AC-06 candidate metrics and baseline method until selected. Performance uses agreed dataset/environment and measured timings, never an invented SLA. Synthetic-only evidence is explicitly limited; real-world validation is not claimed.

## 8. Planned policy verification cases

Proposed future locations: privacy/provider tests in backend AI modules, store-permission tests, frontend disclosure checks, and `docs/evidence/` evaluation records. No executable tests implemented or provider invoked.

| ID | Planned case | Expected outcome |
| --- | --- | --- |
| P-01 | Attempt to import/use real customer data before written approval | Blocked; no collection, provider transmission or evaluation |
| P-02 | Synthetic manifest and repeatable fixtures | Provenance/type/seed/version recorded; no real contact routability or embedded identities |
| P-03 | Provider/model or privacy review missing | No provider call; disclosed unavailable/approval-required state |
| P-04 | Provider key accidentally included in frontend/log/prompt/evidence input | Validation/security check rejects exposure; secret absent from output artifacts |
| P-05 | Customer message contains contact details or disclosure instructions | Minimize/review; no instructions-driven data leak or automatic action |
| P-06 | Foreign-store retrieval, staff revocation or cached context reuse | Denied before context generation/transmission; no other-store result |
| P-07 | Budget absent/exhausted; retries/concurrent calls | No new unauthorized spend; approved hard cap includes retries/concurrency |
| P-08 | Timeout/rate-limit/provider failure | Bounded selected retry policy; honest failure, no fake draft or unreviewed provider switch |
| P-09 | Debug logging/evaluation evidence | Sufficient approved reproducible input references; no raw secrets/identifiers or unapproved message retention |
| P-10 | Approved local retention/reset and backup/provider distinction | Removal/access behavior matches approved policy; no false provider-deletion claim |
| P-11 | All six feature evaluations with expected references | Rubric applied, critical failures separated; blocked cases not labeled passed |
| P-12 | Synthetic forecast benchmark reported | Generator/split/metric/scores and synthetic limitation disclosed; no real-world accuracy claim |
| P-13 | AI numerical claims versus deterministic ground truth | Arithmetic sourced from code/records, not LLM invention |
| P-14 | Seller review and outage UI | Suggestion/estimate/service limitation labels; no external send or autonomous change |

## 9. Decisions, traceability and next gate

DP-01 data mode is resolved: user approved synthetic-only demo/evaluation, with real data separately reviewed and approved before use. DP-02 provider/terms, DP-03 future cost/service limits, DP-04 retention/privacy evidence, DP-05 optional deterministic fallback, and DP-06 acceptance/sample plan remain **[DECISION REQUIRED]**. Record approvals by actor/date without inferring instructor review. All prior DR/AD/AC unresolved items remain; PLAN-06 does not finalize financial definitions or choose forecasting thresholds/models.

FR-19 maps to section 6/P-09; FR-20 to disclosure/rubric; AIR-01–03/07/09–10 to minimized grounding, deterministic arithmetic and seller review; AIR-04–06/08 to six-feature evaluation and PLAN-05 gates; NFR-01–02/04/06/09–10 to store access, privacy, measured performance, explainability, service limits and honest outcomes. D-06/D-07 are only resolved to the extent explicitly approved, not by recommendations.

Next is a planning-gate review: obtain missing decisions needed for dependent work before explicitly starting SETUP-01. No setup or application task is started by this record. Provider may remain undecided while unrelated setup is later authorized, but provider integration and real-data use remain blocked.

## 10. Documentation verification evidence

Inspection commands: `git status --short --branch`; `rg --files --hidden -g '!.git'`; `Get-Content docs/decisions/analytics-and-ai.md`; relevant open-decision sections of `Get-Content docs/decisions/auth-and-store.md`. Outcomes: docs branch, clean tree, prerequisite documents present; no dataset/provider configuration to execute. No provider keys or real customer dataset was read or used; proposal author information is source documentation, not evaluation data.

PowerShell assertions using `Get-Content -Raw`, `[regex]::Matches`, `Group-Object` and `Compare-Object` printed `PASS: approved synthetic policy, 10 sections, 6 feature rubrics, 12 checklist items, 14 unique future cases, provider/budget/retention gates`, exit 0. Manual review confirmed the user-selected data policy, no premature provider approval, separation of local/provider retention, no authorized spend before review, six-feature rubric coverage and explicit limits on synthetic evidence. This checks policy completeness, not application behavior or absence of all secrets throughout Git history.

Commands: `git diff --check`, `git diff --stat`, `git diff` (empty tracked-change output); `git diff --no-index --stat -- NUL docs/decisions/data-and-provider.md` (new-file summary); `git diff --no-index --check -- NUL docs/decisions/data-and-provider.md` (no whitespace errors); `git status --porcelain=v1 --untracked-files=all` (only this new document). Git warned of possible LF-to-CRLF conversion. No-index diff uses exit 1 for differences, not a failed application check. Final size is reported in chat.

No application tests, external vendor requests or model evaluation apply to this documentation-only task. Only this new decision file is changed; no automatic commit.
