# Synthetic receipt evaluation

From the repository root, score the frozen batch without credentials or network access:

```powershell
python evaluation/benchmark.py score --human evaluation/human.json --output frontend/src/evaluation.json
```

Use the backend requirements. The PNG fixtures were generated with Pillow 10.4.0. The generator uses seed 4317, six sequential receipt IDs, alternating discounts, an 8% printed tax rounded half-up, and partial occlusions on C and F. The showcase INR receipt is separate. Every generated case was included. The six supplied responses in human.json were AI-assisted visual transcriptions of review-sheet.png. Four matched the labels and two were unreadable (null). This run provides no independent measurement of human accuracy. The filename and CLI option are retained for reproducibility.

The first model reading is the AI-only prediction. For selective review, the production analyze function uses both readings. Random review samples exactly the same number without replacement using seed 4317. Full review applies those AI-assisted responses to all six. All policies use the same ground truth, frozen model outputs and AI-assisted answers. Errors detected counts initial AI total errors routed for inspection, checked against labels offline. Errors corrected counts routed AI errors for which the reviewer supplied the labeled value. A reviewer abstention supplies no correction. The scorer also reports abstentions and new errors introduced. Costs assume USD 0.75 per requested review, even on abstention, and exclude model usage. They are estimates, not transactions. Corrections divided by zero reviews is undefined.

predictions.json retains image hashes, prompts, model names, provider response IDs, timestamps and schema-validated readings. The app displays the generated frontend/src/evaluation.json. To generate a fresh comparison, copy the evaluation directory into a separate checkout, generate the fixtures, set the backend Gemini configuration, and run collect with an empty predictions file location (remove the copy of predictions.json first). The collector resumes missing images and detects changed image hashes. The original recording used GEMINI_MODEL=gemini-3.1-flash-lite. A new API run can produce different readings.

```powershell
python evaluation/benchmark.py generate
python evaluation/benchmark.py collect
python evaluation/benchmark.py score --human evaluation/human.json
```

The recorded run had zero initial AI errors. It cannot estimate error-detection recall, correction uplift, calibrated confidence, or real-world cost savings.
## Separate readability challenge

Three fixed synthetic captures use a blur, a cropped lower edge, or a fold across printed amounts. Labels were set from the original print layout before degradation. The production policy received only the degraded image through two real Gemini calls. All three cases are retained.

| Capture | Original total | First / second total | Policy decision |
|---|---:|---|---|
| Blur | 19.44 | 19.44 / 19.44 | No finding |
| Cropped | 51.30 | unavailable / unavailable | Review the missing total |
| Fold | 60.26 | 60.26 / 60.26 | Review subtotal disagreement and failed arithmetic |

The crop removed the printed total. An abstention is appropriate. A reviewer looking at the same crop may also need to request a better source. Both fold totals were correct despite a component disagreement. No independent reviewer or payment participated in this challenge. These three cases demonstrate routing outcomes only. In a new checkout, run `python evaluation/challenge.py` with the recorded Pillow version to check image hashes and reuse frozen results. For fresh provider calls, move the copy of challenge/results.json aside first. [Inputs and provider readings](challenge)
