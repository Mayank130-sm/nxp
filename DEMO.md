# NeuroRx: 3-minute demo script

Follows the slide order: problem, solution, users, architecture, TinyFish, scalability and use case.
Numbers below come from `results/slide_numbers.md` (regenerate with `python scripts/slide_numbers.py`). Say them as they appear there.

**Before you start:** open the app on the Ranking page (`make dev`, or the static Vercel build). Have a second tab on `#/graph`. Zoom the browser to 100%.

---

## 0:00-0:25 Problem (slide 1, Ranking page hero)

> "Adult neurogenesis is impaired in Alzheimer's, and papers report that dozens of approved drugs raise it or lower it. But the evidence is spread across thousands of papers, in different species, with different markers, and it often disagrees. A lab can't read it all, so it can't tell which drug is worth a bench test."

*Show:* the hero headline. Point at the three live tiles (**1,536 papers processed, 1,288 verified claims, 28 drugs scored**).

## 0:25-1:00 Solution (slide 2, Ranking cards)

> "NeuroRx turns that literature into a graph where every drug claim links to a paper, gets a 0-100 confidence grade, and is flagged when contradicted. It ranks drugs, and every rank comes with a plain-language reason."

*Do:* scroll the ranked cards. Point at a teal ring (memantine, a positive control), a coral **Safety flag** (ethanol or morphine, negative controls), and a **conflict** badge. Click **Memantine**.

*Show on the detail page:* the score breakdown bars, the verbatim quote with the green **verified** tick, and the PMID link. Say: "Every quote is checked to be an exact substring of the source. If it isn't, the claim is thrown away. 98% of claims the model proposed passed (1,614 proposed, 24 rejected); the rest never reach this screen."

## 1:00-1:20 Users (slide 3)

> "The users are preclinical labs and translational researchers choosing which approved drug to test next in an Alzheimer's neurogenesis model, plus reviewers who need to audit why a drug was suggested."

*Show:* the amber strip "Hypothesis for lab testing, not a treatment claim." and the conflict panel (side-by-side studies that disagree, e.g. on memantine's proliferation effect). "We never hide disagreement."

## 1:20-1:50 Architecture (slide 4, Methods page, pipeline strip)

> "Search and fetch gather the papers, PubMed supplies the abstract backbone. A local LLM reads sentence windows behind two gates: a keyword gate, then a yes/no gate, then a strict-schema extraction. Quote grounding discards anything not literally in the text. Then grading, contradiction detection, ranking, and a NetworkX graph, served by FastAPI to this React app."

*Do:* go to **Methods**, point at the pipeline strip and the stacked scoring-weights bar (replication 25, design 25, markers 20, species 20, dose/BBB 10).

## 1:50-2:25 TinyFish (slide 5, "Powered by TinyFish" panel)

> "TinyFish is the web layer, and these are real call counts from our own log. **Search** found ranked open-access URLs for every drug and stage. **Fetch** turned the open-access pages into clean Markdown so we could read Methods and Results, where species, dose and markers live. And **Agent** handles what has no API: it drove ClinicalTrials.gov and drug-label pages to bring back trial lists and blood-brain-barrier notes. Search and Fetch are free-tier, with caching, rate limiting and a call log."

*Show:* the three counters (search 85, fetch 89, agent 66 live calls at the time of writing, 240 in total; read the live panel).

## 2:25-2:50 Validation and honesty (slide 6, Methods validation card)

> "We tested against controls. Fluoxetine, lithium, metformin and memantine surface pro-neurogenic evidence; ethanol and morphine surface suppression and get safety flags. All seven controls came out as expected on the larger corpus. With the first, smaller corpus dexamethasone was missed because its papers talk about glucocorticoids as a class; we did not tune for it, and it was recovered only after we fetched more papers. Two positive controls, fluoxetine and metformin, still rank low (scores 17 and 20) despite mostly pro-neurogenic papers, and we have not tuned for that either. We also ran an ablation, and on this small control set a plain vote count separates controls better than our grading (gap 14.4 against 10.5), so we say that. Grading may even be hurting on this corpus, and we have not investigated why. The grading's value is the per-claim explanation and the penalties for conflicts and single-paper evidence."

## 2:50-3:00 Scalability and use case (slide 7, Graph page)

> "Same pipeline, any disease or process: swap the seed list and vocabulary. Here is the graph: drugs, pathways, stages, and Alzheimer's, with edge thickness showing confidence. Click a node to open its evidence."

*Do:* open **Graph**, click a drug node, show the drawer with connections, close with the **Focus** control.

---

## If something goes wrong

- **Backend down:** the app falls back to the static JSON in `frontend/public/data/` automatically. Nothing visible changes.
- **Graph slow to settle:** press the fit-to-screen button.
- **Question you can't answer from the data:** say "unknown" — that is the product's rule.

## Likely questions

- *"Is this a treatment recommendation?"* No. Hypothesis for lab testing, stated on every page.
- *"How do you know the extraction is accurate?"* Quotes are verified programmatically (98%); claim-detection precision and recall are 89% / 89% on a 100-sentence gold set labelled by two AI annotators (kappa 0.72), not by humans, so treat it as a sanity check until a person relabels it (`scripts/make_human_sheet.py`).
- *"Why are scores below 100?"* Evidence is mostly rodent, with few markers and doses stated; the score reflects that, deliberately.
