In README.md, the "Why This Is Defensible" section has stale content left over from
an earlier version that was never removed when it was upgraded to the three-tier
severity evaluation design. Fix as follows:

1. Delete the old intro sentence referencing "Controlled evaluation (src/evaluation.py)
   runs 20 seeded trials per corruption scenario (140 total evaluations across 120
   corrupted and 20 clean runs):" — keep only the sentence describing the three-tier
   (subtle/moderate/obvious) design, since that's what's actually implemented in
   src/validation.py.

2. Delete the entire old flat table (the one with columns Scenario/Trials/Precision/
   Recall/F1 Score/False Positive Rate, showing uniform 100%/1.000 values and an
   "Overall Summary | 140" row) — it's superseded by and contradicts the newer
   severity-tiered table below it.

3. Keep only the newer table (columns: Scenario / Corruption Type, Subtle Recall,
   Moderate Recall, Obvious Recall, False Positive Rate, Notes on Detection
   Thresholds) and verify its rows render correctly as a single clean markdown table
   with no orphaned cells.

4. Fix the "Clean Control Data" row specifically — check src/validation.py's actual
   output for this scenario and make sure the row reflects real values, not a
   leftover from the deleted table.

5. Everywhere else in the README that says "src/evaluation.py", change it to
   "src/validation.py" to match what's actually in the Architecture section and
   the repo's file listing.

6. After editing, render the README locally (or check GitHub's preview) and confirm
   there is exactly ONE evaluation table, its numbers are internally consistent with
   the "Summary by Severity Level" row and the prose claims above/below it, and
   nothing in the Architecture or API Reference sections contradicts it.

Do not change any code in src/validation.py or src/simulate.py — this is a
documentation-only fix. If you're not sure what the correct current numbers are,
re-run the actual evaluation (python -m scripts or however validation.py is
invoked) and use its real output rather than guessing.
