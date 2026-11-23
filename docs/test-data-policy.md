# SellerOS synthetic test-data policy and seed strategy

DATA-01, 23 November 2026. This policy implements the approved PLAN-06 synthetic-only boundary for test, demo, and evaluation records. It does not create a seed command, import data, alter a database, or approve any provider use.

## 1. Default policy and data provenance

SellerOS demo, automated-test, and evaluation records are **synthetic-only**. Every record must be fabricated specifically for SellerOS; it must not be copied, transformed, sampled, inferred, or anonymized from a production export, seller account, customer conversation, address book, payment record, or real-person contact detail.

Allowed sources are limited to:

- deterministic test factories in `backend/tests/factories/`;
- hand-authored, wholly fictional fixture definitions reviewed with the code; and
- a future deterministic generator whose source, version, seed, and output manifest are recorded.

`@example.test` identifiers are the required convention for synthetic accounts and contact-like fields. Synthetic customer/store/product names must be fictional and must not be deliberately patterned after a real seller or person. A data item with uncertain provenance is treated as prohibited until it is replaced with an unambiguously synthetic value.

**Production export is prohibited for demonstrations by default.** Real or authorized data needs separate written approval covering purpose, provenance/permission, minimization, access, provider transfer, retention, deletion, backups, and applicable institutional review. Pseudonymization alone is not approval or proof that the data is no longer personal.

## 2. Mandatory synthetic labeling

Every future fixture manifest, generator output, demo screen, evaluation artifact, and exported screenshot/table that contains seeded values must visibly state `SYNTHETIC DATA — NOT SELLER PERFORMANCE`.

A future fixture manifest must contain at least:

| Field | Required value |
| --- | --- |
| Fixture identifier/version | Stable human-readable identifier and revision |
| Provenance | `synthetic` only; never a vague description such as “sample” |
| Generator/source | Factory module, fixture file, or generator revision |
| Determinism | Seed or fixed construction steps sufficient to reproduce it |
| Store isolation | Synthetic store identifiers and the intended owner/staff/revoked cases |
| Coverage | Intended normal, empty, invalid, and cross-store cases |
| Limits | Explicit statement that values are not real sales, forecasts, or outcomes |

Do not label a live API response as synthetic unless its underlying database was loaded from such an identified synthetic fixture. Conversely, demo fixtures must remain separate from production API transport and must not silently replace unavailable live data.

## 3. Current and future seed strategy

### Current implementation

The only existing synthetic record builders are the deterministic account/store factories in `backend/tests/factories/`. Django tests create a disposable PostgreSQL test database, apply migrations, and destroy that database after the test run. This is the only approved reset mechanism today.

There is no application demo seed command, checked-in dataset, production import path, or persistent demo database. `data/sample/` contains documentation only. No task may treat an empty directory or a placeholder as authorization to load records.

### Future seed-command design (not implemented)

A later approved management command may load a reviewed synthetic manifest only when all of the following are true:

1. The operator explicitly selects a known disposable local/demo target; the command must refuse an unrecognized or production-designated target.
2. The manifest states `synthetic` provenance and passes schema/provenance validation before any write.
3. The command derives all store ownership/membership links through normal model validation and never bypasses store permissions or database constraints.
4. The command prints a synthetic-data warning and creates an auditable manifest reference, but never logs credentials, tokens, customer-like free text, or secrets.
5. Reset is a separate explicit operation, never an implicit side effect of normal seeding.

No command name, flags, destructive mechanism, or persistent storage target is approved by this document. Implementing one requires the retention/reset decision below and a dedicated data task.

## 4. Reset and retention

| Context | Current rule |
| --- | --- |
| Automated Django tests | Use the disposable PostgreSQL test database created and destroyed by the test runner. Do not point tests at a shared or production database. |
| Source-controlled factories/manifests | Retain only fictional source definitions and metadata; never retain generated database dumps, raw exports, tokens, credentials, or customer-like free text. |
| Local demo database | No persistent seed/reset workflow is approved yet. Do not load or reset it automatically. |
| Screenshots/evaluation evidence | Retain only clearly labeled synthetic, minimized evidence. Never include secrets, raw authorization headers, or real-person details. |

**[DECISION REQUIRED] DATA-01-R1:** authorize the persistent local-demo reset operator, retention period, deletion procedure, backup handling, and evidence-retention period. This is the PLAN-06 DP-04 gate applied to seed data. Until it is resolved, a future seed command must not offer a destructive reset against a persistent database.

## 5. Pre-load review checklist

Complete this review before loading any test/demo records outside the Django test runner:

- [ ] The source is one of the allowed synthetic sources and has no real-data derivation.
- [ ] A reviewer has checked fictional names, `@example.test` contacts, and absence of credentials, payment data, addresses, conversations, and sensitive attributes.
- [ ] The manifest carries all required synthetic labels and reproducibility metadata.
- [ ] The target is confirmed disposable/local-demo, not shared production or an unknown database.
- [ ] Store ownership, staff/revocation, and at least two isolated stores are represented where the relevant model/API exists.
- [ ] The values do not claim real revenue, forecast accuracy, seller performance, or AI outcomes.
- [ ] Planned reset/retention behavior is either covered by the Django test runner or has the DATA-01-R1 approval.

Record the reviewer, date, manifest identifier, target type, and result beside the future manifest/evaluation evidence. A failed or incomplete review blocks loading; it is not a warning that may be bypassed.

## 6. Security and authorization boundaries

Synthetic data does not relax authentication, store isolation, role checks, validation, secret handling, or provider approval. Fixtures must use normal model/API paths where the task is testing those paths. A seed must not assign an account to another store, embed a privileged token, or create a route around server-side authorization.

Testing requires at least two isolated fictional stores whenever an API exposes store-owned records. Cross-store reads, filters, counts, detail lookups, and mutations must deny safely without disclosing another store's data. Existing AUTH-04 and AUTH-06 tests are evidence for the implemented account/store surface, not authorization to claim future product/order isolation without their own tests.

## 7. Limits and next dependency

Synthetic data can verify workflow, arithmetic, validation, isolation, empty states, and deterministic evaluation behavior. It cannot demonstrate real seller demand, forecast accuracy, business impact, representative usability, or production performance.

Future product/order/inventory/analytics tasks may add only the fixtures their approved models and contracts require. Before a persistent demo seed command or dataset is implemented, resolve DATA-01-R1 and retain the PLAN-06 provider/privacy decisions: provider selection (DP-02), cost limits (DP-03), deterministic fallback (DP-05), and evaluation plan (DP-06).

## 8. Policy verification evidence

Policy review was performed against [the PLAN-06 data/provider decision](decisions/data-and-provider.md), [shared factory guidance](testing/factories.md), [current factory code](../backend/tests/factories/accounts.py), current `.gitignore`, and `data/sample/README.md`. The repository currently contains factory code and documentation but no seed command or sample dataset.

Verification for this documentation task checks that this policy states the synthetic-only provenance rule, production-export prohibition, labeling metadata, current test reset boundary, persistent-reset decision gate, and pre-load review checklist. It does not establish that all Git history, local databases, backups, or machines are free of sensitive data.
