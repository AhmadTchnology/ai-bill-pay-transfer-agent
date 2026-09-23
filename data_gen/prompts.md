# Data Generation — Schemas & Prompts

Per the competition brief, all mock data was **generated with an LLM (GLM-5.3)
from the schemas below, then hand-edited for realism**.

## 1. Mock wallet — `wallet_schema.json`

The wallet contents (`data/seed_data.json`) were generated from this schema.
The generation prompt intentionally required:

- **duplicate and similar contact names** — "أحمد", "أحمد علي", "أحمد حسين",
  plus "علي", "علي حسين", "حسين" — to exercise the disambiguation flow;
- realistic Iraqi phone prefixes (0770/0780/0750) and local wallet providers
  (زين كاش, آسيا حوالة, فاست باي);
- billers across categories (كهرباء, ماء, انترنت, موبايل ×3, غاز) with one
  biller (غاز المدينة) deliberately **not linked** to the demo user, to test
  the honest "not in your registered billers" failure;
- transaction history mixing transfers and bill payments.

## 2. Test set — category definitions in `tests/_make_testset.py`

Test requests were drafted by GLM-5.3 from these category definitions, then
hand-edited for dialect realism (Iraqi forms like "دز", "ابعت", "گلي",
"چبي", "شلون", "مي" for water):

| Category | What it exercises |
|---|---|
| simple_transfer / simple_bill | happy path with confirmation variants (نعم/اكيد/ايوة/زين/yes) |
| ambiguous_contact / ambiguous_biller | "which Ahmed?" — must ask, never pick |
| ambiguous_resolved_specific | full name "أحمد حسين" resolves immediately |
| missing_recipient / missing_biller / bill_missing_amount | gather-what's-missing dialogue |
| insufficient_funds (+combined, +after_payment) | honest early rejection, no partial execution |
| unknown_contact / unknown_biller / unlinked_biller | "ما ألقى..." with helpful lists |
| malformed / smalltalk | nonsense → polite clarification, never a guess |
| two_in_one (+cancel, +missing_amounts) | one sentence = two transactions; one card; all-or-nothing |
| cancel_flow | "لا", "لا زين", "كنسل", unclear reply → nothing executes |
| repeat_transfer_legit | same request twice = two legitimate payments (new idempotency keys) |
| history_after_payment / query | balance & history reporting |
| api_idempotency (A01–A03) | wallet-level double-submit / retry / distinct-key proofs |

Each case also records the expected NLU output, so the harness can **replay**
the deterministic core without an API key, and can run **live** end-to-end
with the real GLM-5.3 NLU.

## 3. Wallet generation prompt (used with GLM-5.3)

> You are generating mock data for an Iraqi mobile-wallet demo. Follow the
> JSON schema in wallet_schema.json exactly. Users must include one demo user
> (سامر) with balance 450,000 IQD. Contacts MUST include three near-duplicate
> Ahmeds ("أحمد", "أحمد علي", "أحمد حسين") and an Ali/Hussein cluster. Use
> realistic Iraqi phone numbers (07xx) and wallet providers (زين كاش, آسيا
> حوالة, فاست باي). Billers: كهرباء بغداد, ماء بغداد, إنترنت الفردوس,
> آسياسيل, زين العراق, كورك تيليكوم, غاز المدينة — link all but غاز to the
> demo user. History: 6 mixed transfer/bill transactions over the past 2
> weeks. Output only valid JSON.
