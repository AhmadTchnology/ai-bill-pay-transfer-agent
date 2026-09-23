# Test Results — Bill Pay & Transfer Agent

- Date: 2026-09-23 21:20
- Mode: **LIVE** (real GLM-5.3 NLU)
- Test set: 58 cases (55 Iraqi-dialect chat cases + 3 wallet idempotency scripts)
- Starting balance per case: 450,000 IQD (wallet reset before each case)

## Summary

| Category | Pass | Fail |
|---|---|---|
| ambiguous_biller | 1 | 0 |
| ambiguous_contact | 2 | 0 |
| ambiguous_resolved_specific | 2 | 0 |
| api_idempotency | 3 | 0 |
| bill_missing_amount | 1 | 0 |
| cancel_flow | 5 | 0 |
| confirm_english | 1 | 0 |
| history_after_payment | 1 | 0 |
| insufficient_after_payment | 1 | 0 |
| insufficient_funds | 2 | 0 |
| insufficient_funds_combined | 1 | 0 |
| malformed | 8 | 0 |
| missing_biller | 1 | 0 |
| missing_recipient | 1 | 0 |
| query | 3 | 0 |
| query_flexible | 1 | 0 |
| repeat_transfer_legit | 1 | 0 |
| simple_bill | 6 | 0 |
| simple_transfer | 8 | 0 |
| smalltalk | 1 | 0 |
| two_in_one | 2 | 0 |
| two_in_one_cancel | 1 | 0 |
| two_in_one_missing_amounts | 1 | 0 |
| unknown_biller | 2 | 0 |
| unknown_contact | 1 | 0 |
| unlinked_biller | 1 | 0 |

**Total: 58/58 passed (100%)**

## Cases

| ID | Category | First request | Expected outcome | Result | Notes |
|---|---|---|---|---|---|
| T01 | simple_transfer | حول 50000 لزينب | ask_confirm, executed | PASS | balance=400000 new_txns=1 |
| T02 | simple_transfer | ابعت 25000 لمحمد الجبوري | ask_confirm, executed | PASS | balance=425000 new_txns=1 |
| T03 | simple_transfer | حول لي 100000 لنور | ask_confirm, executed | PASS | balance=350000 new_txns=1 |
| T04 | simple_transfer | سوي تحويل 75000 لفاطمة | ask_confirm, executed | PASS | balance=375000 new_txns=1 |
| T05 | simple_transfer | دز 12000 لعمر التميمي | ask_confirm, executed | PASS | balance=438000 new_txns=1 |
| T06 | simple_transfer | حول مية الف لمريم عبد الله | ask_confirm, executed | PASS | balance=350000 new_txns=1 |
| T07 | simple_transfer | ابعت 15000 للدكتورة ليلى | ask_confirm, executed | PASS | balance=435000 new_txns=1 |
| T08 | simple_transfer | كمل حوالة 30000 لكرار | ask_confirm, executed | PASS | balance=420000 new_txns=1 |
| T09 | bill_missing_amount | دفع فاتورة الكهرباء | ask_amount, ask_confirm, executed | PASS | balance=415000 new_txns=1 |
| T10 | simple_bill | سدد فاتورة الماء 8000 | ask_confirm, executed | PASS | balance=442000 new_txns=1 |
| T11 | simple_bill | دفع انترنت الفردوس 30000 | ask_confirm, executed | PASS | balance=420000 new_txns=1 |
| T12 | simple_bill | شحن رصيد آسياسيل 15000 | ask_confirm, executed | PASS | balance=435000 new_txns=1 |
| T13 | simple_bill | شحن زين العراق 20000 | ask_confirm, executed | PASS | balance=430000 new_txns=1 |
| T14 | simple_bill | عبئ كورك 10000 | ask_confirm, executed | PASS | balance=440000 new_txns=1 |
| T15 | simple_bill | ادفع فاتورة المي 12000 | ask_confirm, executed | PASS | balance=438000 new_txns=1 |
| T16 | ambiguous_contact | حول 50000 لأحمد | ask_disambiguation, ask_confirm, executed | PASS | balance=400000 new_txns=1 |
| T17 | ambiguous_contact | ابعت 20000 لعلي | ask_disambiguation, ask_confirm, executed | PASS | balance=430000 new_txns=1 |
| T18 | ambiguous_resolved_specific | حول 30000 لأحمد حسين | ask_confirm, executed | PASS | balance=420000 new_txns=1 |
| T19 | ambiguous_resolved_specific | ابعت 70000 لاحمد علي | ask_confirm, executed | PASS | balance=380000 new_txns=1 |
| T20 | missing_recipient | حول 20000 | ask_recipient, ask_confirm, executed | PASS | balance=430000 new_txns=1 |
| T21 | missing_biller | دفع فاتورة | ask_which_biller | PASS | balance=450000 new_txns=0 |
| T22 | malformed | ابعت شي | clarify | PASS | balance=450000 new_txns=0 |
| T23 | malformed | حول | clarify | PASS | balance=450000 new_txns=0 |
| T24 | malformed | سدد | clarify | PASS | balance=450000 new_txns=0 |
| T32 | malformed | شنو هذا؟ | clarify | PASS | balance=450000 new_txns=0 |
| T33 | malformed | احجبنة فلوت احه | clarify | PASS | balance=450000 new_txns=0 |
| T34 | malformed | هههههه | clarify | PASS | balance=450000 new_txns=0 |
| T35 | malformed | 458 | clarify | PASS | balance=450000 new_txns=0 |
| T36 | malformed | توك تؤبرني | clarify | PASS | balance=450000 new_txns=0 |
| T44 | smalltalk | شكرا چبي | clarify | PASS | balance=450000 new_txns=0 |
| T25 | insufficient_funds | حول 900000 لزينب | rejected_insufficient | PASS | balance=450000 new_txns=0 |
| T26 | insufficient_funds | دفع فاتورة كهرباء 500000 | rejected_insufficient | PASS | balance=450000 new_txns=0 |
| T27 | insufficient_funds_combined | حول 400 الف لزينب وادفع فاتورة الكهرباء 100 الف | rejected_insufficient | PASS | balance=450000 new_txns=0 |
| T28 | unknown_contact | حول 25000 لسيف | contact_not_found | PASS | balance=450000 new_txns=0 |
| T29 | unknown_biller | ادفع فاتورة النجرة | biller_not_found | PASS | balance=450000 new_txns=0 |
| T30 | unknown_biller | شحن رصيد اورنج 15000 | biller_not_found | PASS | balance=450000 new_txns=0 |
| T31 | unlinked_biller | ادفع فاتورة غاز المدينة 20000 | biller_not_found | PASS | balance=450000 new_txns=0 |
| T37 | two_in_one | دفع فاتورة الكهرباء وابعت 10000 لزينب | ask_amount, ask_confirm, executed_both | PASS | balance=405000 new_txns=2 |
| T38 | two_in_one | حول 20000 لنور وشحن كورك 10000 | ask_confirm, executed_both | PASS | balance=420000 new_txns=2 |
| T39 | two_in_one_missing_amounts | سدد فاتورة الماء وادفع الانترنت | ask_amount, ask_amount, ask_confirm, executed_both | PASS | balance=412000 new_txns=2 |
| T40 | query | كم رصيدي؟ | balance_reported | PASS | balance=450000 new_txns=0 |
| T41 | query | شو آخر حركاتك؟ | history_reported | PASS | balance=450000 new_txns=0 |
| T42 | query | شنو رصيد المحفظة؟ | balance_reported | PASS | balance=450000 new_txns=0 |
| T43 | query_flexible | وين تروح فلوسي؟ | balance_reported|history_reported|clarify | PASS | balance=450000 new_txns=0 |
| T45 | cancel_flow | حول 30000 لزينب | ask_confirm, cancelled | PASS | balance=450000 new_txns=0 |
| T46 | cancel_flow | دفع فاتورة كهرباء 35000 | ask_confirm, not_executed | PASS | balance=450000 new_txns=0 |
| T47 | cancel_flow | حول 30000 لزينب | ask_confirm, cancelled | PASS | balance=450000 new_txns=0 |
| T48 | cancel_flow | حول 50000 لأحمد | ask_disambiguation, cancelled | PASS | balance=450000 new_txns=0 |
| T49 | cancel_flow | دفع فاتورة الكهرباء | ask_amount, cancelled | PASS | balance=450000 new_txns=0 |
| T50 | repeat_transfer_legit | حول 50000 لزينب | ask_confirm, executed, ask_confirm, executed | PASS | balance=350000 new_txns=2 |
| T51 | ambiguous_biller | شحن موبايل 15000 | ask_disambiguation, ask_confirm, executed | PASS | balance=435000 new_txns=1 |
| T52 | confirm_english | حول 20000 لنور | ask_confirm, executed | PASS | balance=430000 new_txns=1 |
| T53 | insufficient_after_payment | حول 400000 لزينب | ask_confirm, executed, rejected_insufficient | PASS | balance=50000 new_txns=1 |
| T54 | two_in_one_cancel | دفع فاتورة الكهرباء وابعت 10000 لزينب | ask_amount, cancelled | PASS | balance=450000 new_txns=0 |
| T55 | history_after_payment | حول 20000 لزينب | ask_confirm, executed, history_reported | PASS | balance=430000 new_txns=1 |
| A01 | api_idempotency | same Idempotency-Key twice -> one debit, same transaction id | double_transfer_same_key | PASS | txn=txn_196e3291e348 dup=True balance=425000 txns=1 |
| A02 | api_idempotency | executor-level retry with same key -> duplicate flag, one debit | executor_retry_same_key | PASS | retry flagged duplicate, single debit: balance=440000 |
| A03 | api_idempotency | different keys -> two debits (legitimate repeat still works) | legit_two_transfers | PASS | two distinct txns, balance=410000 |