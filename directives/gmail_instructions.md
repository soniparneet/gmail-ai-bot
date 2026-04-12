# Gmail AI Bot Instructions

## Mission

Aggressively identify low-value, non-urgent, non-actionable emails that are safe to review later for deletion, while strictly preserving important emails.

The system should significantly reduce inbox clutter without ever deleting emails automatically.

---

## Polling Rules (Real-Time)

- Poll Gmail every 60 seconds.
- Only review emails that match:
- `label:INBOX`
- not already labeled `AI Processed`
- received in the last 20 minutes
- Ignore emails from the account owner's own addresses.

---

## Safety Rules (STRICT)

- Never remove the `INBOX` label.
- Never delete emails automatically.
- Always add `AI Processed` after review.
- Only add `AI_Verify_to_Delete` when the email is likely clutter.
- If uncertain -> preserve the email.

---

## Core Classification Philosophy

Do NOT only detect "marketing".

Instead classify based on:

-> "Is this email LOW VALUE and safe to ignore or delete later?"

---

## LOW VALUE (Mark as AI_Verify_to_Delete)

Mark as `AI_Verify_to_Delete` if ANY of the following apply:

### 1. Marketing & Promotions

- discounts, offers, deals
- product promotions
- upgrade nudges
- newsletters
- cold outreach
- event promotions

### 2. Notifications & Automated Emails

- social notifications
- app alerts
- summaries and digests
- update notifications
- activity notifications

### 3. Subscriptions & Bulk Emails

- newsletters
- blog updates
- release notes
- community updates
- recurring automated emails

### 4. Low-Signal Outreach

- generic sales emails
- templated B2B outreach
- vendor pitches
- irrelevant follow-ups

### 5. Non-Actionable Emails

- FYI-only emails
- announcements with no action required
- passive updates

### 6. Heuristic Signals

Strongly bias toward LOW VALUE if:

- contains `unsubscribe`
- contains `manage preferences`
- contains `view in browser`
- bulk-style formatting
- promotional tone
- no clear action required
- no personalization
- recurring sender patterns

---

## HIGH VALUE (NEVER MARK AS DELETABLE)

Do NOT mark as `AI_Verify_to_Delete` if ANY of the following:

### Financial / Transactions

- bank alerts
- credit or debit notifications
- invoices, bills, receipts
- statements
- tax documents

### Legal / Compliance

- contracts
- agreements
- policy updates
- legal notices

### Work / Important Communication

- emails requiring response
- project discussions
- approvals or decisions
- direct human communication

### Hiring / Career

- recruiter emails
- interview invites
- job offers

### Calendar / Coordination

- meeting invites
- event confirmations
- scheduling emails

### Security / Account Access

- login alerts
- OTPs
- password resets
- fraud alerts

### Personal / High-Signal

- one-to-one human messages
- known contacts with meaningful content

---

## Decision Rule

- If email is non-urgent + non-actionable + replaceable -> LOW VALUE
- If email is important, actionable, or time-sensitive -> IMPORTANT
- When unsure -> IMPORTANT

---

## Self Address Handling

- The bot should always ignore the primary Gmail profile email address.
- Additional self addresses may be supplied through `AI_BOT_SELF_EMAILS` as a comma-separated list.
- Historical placeholders: `[YOUR_EMAIL_1]`, `[YOUR_EMAIL_2]`

---

## Model Prompt Contract

Provide:

- subject
- sender
- trimmed body/snippet
- presence of unsubscribe and marketing signals when available

Prompt:

Classify this email as LOW_VALUE or IMPORTANT. LOW_VALUE means safe to ignore or delete later. IMPORTANT means it requires attention or should be preserved. Be aggressive in identifying clutter but do not misclassify financial, legal, hiring, calendar, security, or personal emails.

---

## Expected Output

- `Category: LowValue`
- `Category: Important`

---

## Matching Logic

Treat any of these as LOW VALUE:

- `LowValue`
- `low value`
- `marketing`
- `promotional`
- `clutter`

Apply label `AI_Verify_to_Delete`.

---

## Retry Logic

- Retry up to 3 times with exponential backoff
- On failure -> default to IMPORTANT

---

## Historical Classification Endpoint

### Endpoint

POST `/classify-historical`

### Input

- `from_date` in `YYYY-MM-DD`
- `to_date` in `YYYY-MM-DD`

### Behavior

- Fetch emails:
- `label:INBOX`
- within the date range
- Skip emails already labeled `AI Processed`
- Process emails in batches
- Apply the same classification logic as real-time polling

### Actions per Email

If classified as LOW VALUE:

- Apply `AI_Verify_to_Delete`

Always:

- Apply `AI Processed`

Never:

- Remove `INBOX`
- Delete emails

### Safety Controls

- Respect Gmail API rate limits
- Process in batches of 50 to 100 emails per batch
- Add retry handling for API failures
- Log progress for resumability

### Idempotency

- Emails with `AI Processed` must never be reprocessed
- It must be safe to rerun the endpoint multiple times

### Expected Outcome

- Historical inbox cleanup
- A large share of clutter should be tagged as LOW VALUE
- Zero critical email loss

---

## System Objective

The bot should:

- Aggressively surface clutter
- Preserve all important emails
- Enable fast manual cleanup via `AI_Verify_to_Delete`
- Work both in real-time and on historical inbox data
