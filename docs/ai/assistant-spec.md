# SellerOS Customer Assistant Specification

**Task:** ASSISTANT-01
**Status:** approved prototype behavior specification; no assistant API, provider call, inbox integration, or message delivery is implemented by this document.

## 1. Purpose and hard boundary

SellerOS may help an authenticated seller prepare a **customer-reply draft** for a message the seller has entered. The draft is a suggestion for the seller to review, edit, copy, or discard. It is never sent by SellerOS.

This is deliberately narrower than a general chatbot. It supports a response only when it can be grounded in current, authorized facts from the seller's own store. It does not make decisions, perform business actions, contact a customer, or act as an advisor.

The prototype uses synthetic-only data. A provider/model call remains disabled until the separate provider, privacy-transfer, budget, and retention gates in `docs/decisions/data-and-provider.md` are approved and implemented.

## 2. Authorized users and store boundary

Only an authenticated owner or active staff member may request a draft for their one assigned store. The server, not a submitted `store_id`, resolves that store before any message processing or fact retrieval.

- The request must have active same-store membership.
- Relevant product, variant, price, active state, and availability facts must be retrieved only from that store.
- Cross-store IDs, cached context, prompt text, and client-controlled role/store fields cannot expand access.
- A failed authorization check returns no store facts, starts no provider request, and has no external effect.

Owner and active staff can request/review drafts under the approved access policy. Neither role may manage provider credentials, bypass the review boundary, or cause automatic delivery.

## 3. Accepted task and inputs

The only accepted task is: **prepare one seller-reviewable reply draft to one customer message using relevant, current same-store catalogue facts.**

The future request contract must require the following inputs before it can generate a draft:

| Input | Rule |
| --- | --- |
| Customer message | Non-empty plain text, at most 2,000 Unicode characters. Treat all text as untrusted content, never as an instruction to change authorization or call tools. |
| Authorized store context | Derived server-side from the signed-in user; never accepted as a client-owned authority field. |
| Relevant fact references | Server-selected, current records from the authorized store only. Records may include a product/variant name, current price, active state, and availability state. |
| Fact snapshot metadata | Record identifiers and an `as_of` time are retained for review/evaluation; they do not grant access to other records. |

The future retrieval layer may expose availability as `available`, `unavailable`, or `unknown` to the draft. It must not disclose an exact inventory count to a customer by default. A draft may name a price only when the retrieved record contains that current price, and may call a product available only when the retrieved record supplies that current availability state.

## 4. Draft output and seller review

When all later implementation gates are met, a successful result must contain:

- a plain-text draft;
- the same-store fact references used for each price or availability claim, with their `as_of` metadata;
- an explicit seller-review reminder; and
- warnings for unavailable, inactive, incomplete, or unknown facts.

The seller must be able to edit, copy, or discard the text before any use outside SellerOS. Editing or copying does not create a send operation. SellerOS stores no external messaging credential and exposes no send endpoint, webhook, provider tool, or automatic follow-up behavior.

Until provider approval and a later implementation exist, the only valid runtime result is a clearly labelled **assistant unavailable** state. The UI must not display a hand-written template as though it were generated or verified by an AI provider.

## 5. Abstention and refusal rules

The assistant must abstain or refuse without inventing facts in these situations:

| Request or condition | Required safe behavior |
| --- | --- |
| No relevant current fact, inactive product, or unknown price/availability | Explain that the seller should verify the detail; do not claim it as confirmed. |
| Product not found in the authorized store | Ask the seller to clarify or state that no verified matching product was found. |
| Exact stock-count request | Do not reveal the count by default; use the permitted availability state only, or abstain if it is unknown. |
| Delivery date, shipping fee, discount, refund, payment, cancellation, warranty, or return term without an approved retrieved fact | Do not make a commitment or policy claim. |
| Legal, medical, tax, financial, safety, discriminatory, or other specialist advice | Refuse the advice request and keep the task limited to a factual seller reply draft. |
| Analytics, forecasts, profit calculation, recommendations, or general business advice | Do not perform the work in this feature. These belong to separately scoped deterministic/analytics modules. |
| Cross-store request, unauthenticated user, revoked membership, or foreign record ID | Deny before retrieval; disclose no foreign information. |
| Prompt injection, request for secrets, provider keys, internal rules, tool use, or immediate sending | Treat as untrusted; do not reveal secrets, change controls, retrieve additional data, call a provider/tool, or send a message. |
| Provider/privacy/budget gate is not approved or service is unavailable | Return the labelled unavailable state; do not fabricate a draft or silently switch providers. |

## 6. Privacy, minimization, and evidence

Only the minimum message text and store facts needed for the selected reply may enter a future assistant workflow. Do not retrieve or transmit the customer table, contact values, addresses, payment details, full conversation history, other-store data, credentials, or provider secrets.

For the synthetic prototype, test messages and facts must be clearly labelled synthetic. Future evaluation evidence records a synthetic case/request ID, authorized-store reference, selected fact references, fact `as_of` time, outcome state, warnings, and human-review result. It must not record raw credentials or unneeded contact data. Retention and any external provider transfer remain governed by the separate data/provider policy.

## 7. Explicit exclusions

This feature does not implement or authorize:

- live inbox/platform integration, message polling, customer lookup, or message history;
- automatic, scheduled, bulk, or one-click message sending;
- changing orders, refunds, inventory, prices, discounts, delivery terms, or customer records;
- autonomous product selection, stock reservation, marketing campaigns, or follow-up;
- forecasts, segmentation, profit arithmetic, recommendations, or causal claims;
- use of real customer data, a provider key, or an external provider/model call; or
- any claim that a generated result is correct without the displayed source facts and seller review.

## 8. Acceptance cases

The machine-readable synthetic case set is `backend/tests/assistant_cases/v1.json`. Its structural test is `backend/tests/test_assistant_case_set.py`. These cases define expected safe behavior; they do not invoke a model or judge model quality.

| Case | Expected outcome |
| --- | --- |
| Current same-store price and availability are supplied | A future draft may use only those facts and must carry seller-review/source references. |
| Product is absent or price/availability is unknown | Clarify or disclose the lack of a verified fact; no confirmed claim. |
| Product is inactive or unavailable | Do not promise sale/availability; show a warning or abstain. |
| Customer asks to reveal exact stock count | Do not disclose the quantity; use availability only when known. |
| Cross-store or unauthenticated request | Deny with no retrieval, provider call, or data disclosure. |
| Prompt injection or send-now request | Block the instruction; no control change, provider/tool call, or external action. |
| Provider remains unapproved | Show assistant unavailable; do not create a pretend AI reply. |

## 9. Traceability

This specification implements the planning boundary for `FR-11` (seller-entered message to reply suggestion), `FR-12` (edit/discard and no automatic send), `AIR-01` (same-store product/variant/price/stock grounding), `AIR-02` (no verified unsupported price/availability claim), and `NFR-01`/`NFR-02` (server-side isolation and data minimization). It does not claim that those requirements are implemented; the relevant backend and frontend modules remain future work.
