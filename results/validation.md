# NeuroRx validation

All numbers are computed from the database by `scripts/validate.py`.

## Control recovery: 6/7

| Drug | Kind | Expected | Observed | Score | Match |
|---|---|---|---|---|---|
| fluoxetine | positive | pro-neurogenic evidence | 7 papers increase / 0 decrease | 31 | yes |
| lithium | positive | pro-neurogenic evidence | 4 papers increase / 0 decrease | 42 | yes |
| metformin | positive | pro-neurogenic evidence | 3 papers increase / 0 decrease | 42 | yes |
| memantine | positive | pro-neurogenic evidence | 6 papers increase / 0 decrease | 55 | yes |
| dexamethasone | negative | suppression / safety flag | no verified evidence (unknown) | 0 | NO |
| morphine | negative | suppression / safety flag | 3 papers increase / 6 decrease, safety flag | 0 | yes |
| ethanol | negative | suppression / safety flag | 1 papers increase / 4 decrease, safety flag | 0 | yes |

## Ablation: ranking with vs. without evidence grading

Separation = mean rank of negative controls minus mean rank of positive controls (higher is better).

| Method | Positives mean rank | Negatives mean rank | Separation |
|---|---|---|---|
| With evidence grading | 12.5 | 25.5 | 13.0 |
| Without grading (vote count) | 10.0 | 25.5 | 15.5 |

**Interpretation:** Grading did NOT widen the control gap over a plain vote count on this small control set; its value here is the calibrated within-drug ordering, the penalties for conflicts and single-paper evidence, and the per-claim explanations.

## Quote grounding

- Claims proposed by the LLM: 478
- Rejected (quote not an exact substring): 10
- Fraction with verified quote at proposal time: 0.979
- Claims kept after de-duplication: 399

## Extraction vs. gold set

Not computed: `data/labels/gold_sentences.csv` has not been hand-labelled yet.
