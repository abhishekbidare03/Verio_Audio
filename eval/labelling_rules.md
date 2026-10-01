# Labelling rules (gold set + holdout)

How every test ticket was labelled, so anyone can re-label and get the same answer. Based on the reason-code definitions in `support-policy.pdf` §5.

## my_code — why was the money refunded?

| # | Rule |
|---|---|
| R1 | Label the reason the **money was paid**, using the policy definition of each code strictly. |
| R2 | **RETURN-QC-OK only if the return was actually received** (picked up / returned / QC mentioned). If the pickup was missed or still pending and the refund was released anyway, it's an exception → **GW-OTHER**. |
| R3 | **Refund + replacement on the same ticket:** if the refund itself was owed (parcel lost or damaged in transit → LOST-TRANSIT; return completed → RETURN-QC-OK), use that code. If the right remedy was the replacement (product fault, or the fault was fixed) and the refund came on top → **GW-OTHER**. |
| R4 | **"Refund not credited / refund delay" follow-ups:** RETURN-QC-OK if a return, pickup or QC is mentioned; otherwise **UNCLEAR** (the original reason isn't in the ticket). |
| R5 | **Wrong item shipped** has no code of its own → **GW-OTHER**. |
| R6 | The agent note says what was done. Use the customer message **only if the note gives no reason** ("done", "closed", "as discussed"). |
| R7 | Lost, undelivered, delayed in transit, or arrived damaged via courier → **LOST-TRANSIT**. |
| R8 | Product fault refunded with no replacement and no fix → **WTY-BUYBACK** (DOA-REPL only if clearly within 7 days of delivery). |
| R9 | Small fixed amounts that aren't a product price (e.g. Rs 150 for a missed pickup) are compensation → **GW-OTHER**. |
| R10 | Nothing in the note or message explains the refund → **UNCLEAR**. Don't guess. |

## my_real_goodwill — was the money a gesture or exception? (Y/N)

- **Y:** every refund + replacement case (the refund on top of a replacement is the gesture); refunds released before the return was received; compensation amounts; refunds after the issue was fixed.
- **N:** refunds that were owed under the policy, and wrong-item refunds (a shipping error, not a gesture).

## my_repl_given — was a replacement also sent? (Y/N)

Y if the agent note says a replacement / new unit / fresh pair / RMA / reship went out, **whatever the `replacement_issued` flag says**.

## Process

1. First-pass labels drafted with Claude Code, before any model output existed (`gold_set_labelling_1.xlsx`).
2. Reviewed by me (`gold_set_labelling.xlsx`, `holdout.csv`). Changed: gold 3 codes (R2) + 7 goodwill; holdout 1 code (R2) + 1 goodwill.
3. Consistency pass against these rules: 2 more goodwill labels set to Y (R3: TK-249811, TK-251042). No other label broke a rule.
4. Labels were **not** changed to agree with the AI after seeing its answers. Borderline cases where both readings are defensible keep the reviewer's label (e.g. TK-252397: coupon issue, but Rs 6,648 refunded — kept PRICE-ADJ, the AI says UNCLEAR).
