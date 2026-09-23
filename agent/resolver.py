"""Resolver: maps free-text names to wallet contacts/billers.

Ambiguity policy (competition requirement): "two contacts named Ahmed means a
question, not a coin flip". We only auto-accept a match when it is decisively
unique. In particular, if the user's query is a PREFIX of multiple known
names ("أحمد" vs "أحمد" + "أحمد علي" + "أحمد حسين"), we ask — even when an
exactly-named contact exists, because "which Ahmed" is genuinely unclear.
"""

from wallet_api.db import normalize_arabic, score_match

MATCH_THRESHOLD = 0.55


def resolve_contact(contacts: list[dict], name: str) -> dict:
    """contacts: result of the wallet search for `name`.
    Returns {status: unique|ambiguous|not_found, contact?|options?}"""
    if not contacts:
        return {"status": "not_found"}
    scored = [(score_match(name, c["name"]), c) for c in contacts]
    scored.sort(key=lambda x: -x[0])
    best_score, best = scored[0]
    q = normalize_arabic(name)
    best_name = normalize_arabic(best["name"])

    if best_score >= 0.99 and best_name == q:
        # exact name match: still ambiguous if another contact's name EXTENDS
        # the query ("أحمد" also names "أحمد علي", "أحمد حسين")
        extenders = [
            c for _, c in scored[1:] if normalize_arabic(c["name"]).startswith(q)
        ]
        if extenders:
            return {"status": "ambiguous", "options": [best] + extenders}
        return {"status": "unique", "contact": best}

    if len(scored) == 1 and best_score >= MATCH_THRESHOLD:
        return {"status": "unique", "contact": best}
    # non-exact best: accept only when clearly ahead of the runner-up
    if (
        len(scored) > 1
        and (best_score - scored[1][0]) > 0.1
        and best_score >= MATCH_THRESHOLD
    ):
        return {"status": "unique", "contact": best}
    if best_score < MATCH_THRESHOLD:
        return {"status": "not_found"}
    return {"status": "ambiguous", "options": [c for _, c in scored[:4]]}


def resolve_biller(billers: list[dict], name: str) -> dict:
    """Same never-guess policy for billers. Categories like "موبايل" match several
    operators, so a bare category is a question, not a pick."""
    if not billers:
        return {"status": "not_found"}
    scored = [
        (
            max(
                score_match(name, b["name_ar"]),
                score_match(name, b["name_en"]),
                score_match(name, b.get("category", "")),
            ),
            b,
        )
        for b in billers
    ]
    scored.sort(key=lambda x: -x[0])
    best_score, best = scored[0]
    if best_score >= 0.99:
        # exact match still ambiguous if other billers share the category
        same_cat = [
            b for _, b in scored[1:] if b.get("category") == best.get("category")
        ]
        if same_cat and normalize_arabic(name) == normalize_arabic(
            best.get("category", "")
        ):
            return {"status": "ambiguous", "options": [best] + same_cat}
        return {"status": "unique", "biller": best}
    if len(scored) > 1 and (best_score - scored[1][0]) <= 0.05:
        return {"status": "ambiguous", "options": [b for _, b in scored[:4]]}
    if best_score >= MATCH_THRESHOLD:
        return {"status": "unique", "biller": best}
    return {"status": "not_found"}
