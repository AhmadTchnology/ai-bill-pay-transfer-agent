# Test Results — Bill Pay & Transfer Agent

- Date: 2026-09-23 21:38
- Mode: **LIVE** (real GLM-5.3 NLU)
- Test set: 10 cases (55 Iraqi-dialect chat cases + 3 wallet idempotency scripts)
- Starting balance per case: 450,000 IQD (wallet reset before each case)

## Summary

| Category | Pass | Fail |
|---|---|---|
| heldout_ambiguous | 1 | 0 |
| heldout_bill_slang | 1 | 0 |
| heldout_insufficient | 1 | 0 |
| heldout_missing_biller | 1 | 0 |
| heldout_nonsense | 1 | 0 |
| heldout_partial_name | 1 | 0 |
| heldout_refuse | 1 | 0 |
| heldout_transfer | 2 | 0 |
| heldout_two_in_one | 1 | 0 |

**Total: 10/10 passed (100%)**

## Cases

| ID | Category | First request | Expected outcome | Result | Notes |
|---|---|---|---|---|---|
| H01 | heldout_transfer | حول لي 45000 لفاطمة | ask_confirm, executed | PASS | balance=405000 new_txns=1 |
| H02 | heldout_bill_slang | سدد فاتورة النت 25000 | ask_confirm, executed | PASS | balance=425000 new_txns=1 |
| H03 | heldout_transfer | ابعت 60000 لحسين | ask_confirm, executed | PASS | balance=390000 new_txns=1 |
| H04 | heldout_ambiguous | حول 200000 لاحمد | ask_disambiguation, ask_confirm, executed | PASS | balance=250000 new_txns=1 |
| H05 | heldout_insufficient | ادفع فاتورة الكهرباء 600000 | rejected_insufficient | PASS | balance=450000 new_txns=0 |
| H06 | heldout_two_in_one | عبئ كورك 12000 وادفع فاتورة المي 7000 | ask_confirm, executed_both | PASS | balance=431000 new_txns=2 |
| H07 | heldout_partial_name | حول مية الف لمحمد | ask_confirm, executed | PASS | balance=350000 new_txns=1 |
| H08 | heldout_missing_biller | دفع فاتورة | ask_which_biller | PASS | balance=450000 new_txns=0 |
| H09 | heldout_nonsense | خمشة | clarify | PASS | balance=450000 new_txns=0 |
| H10 | heldout_refuse | حول 80000 لزينب | ask_confirm, cancelled | PASS | balance=450000 new_txns=0 |