# Oturum 2 — 2026-10-22 çalıştırmasının ilk prompt'u (birebir)

Bu prompt, yeni ve bağlamsız bir Claude alt ajan oturumuna verildi. Oturum, içinde yalnızca `SPEC.md`, `CONTRACT.md` ve
`PROMPT.md` (= [session2_yazim.md](session2_yazim.md)) bulunan bir klasörde çalıştı. Sonuç: [cleanroom/REPORT.md](../cleanroom/REPORT.md).

```text
You are the "session 2" (clean-room writing session) of a university reverse-engineering assignment. You start fresh. Your ONLY inputs are the files in /home/claude/cleanroom/: SPEC.md (behaviour), CONTRACT.md (interface) and PROMPT.md (your task, in Turkish — read it first and follow it).

STRICT ISOLATION RULES (this is the whole point of the exercise):
- Read ONLY files inside /home/claude/cleanroom/. Do NOT read, list, grep or import anything under /home/claude/ata-dmrl/ or any other project directory, and do not look for an existing implementation anywhere (no searching the filesystem, no pip packages named noncentra). Do not use web search.
- Write all your code inside /home/claude/cleanroom/impl/.
- You may pip install scipy/numpy/pytest (use `pip install --break-system-packages` if needed). Do not use statsmodels or any power-analysis library.
- If something is not in SPEC.md/CONTRACT.md, do not invent it: write it down as "SPEC'te yok".

TASK (summary of PROMPT.md): implement a power-analysis engine for the matched-pairs t test (test id "t-paired", all five modes) and a `gpower-clone` CLI that follows CONTRACT.md exactly (one-line JSON on stdout, integers as JSON integers, error JSON {"error","code","field"}, exit codes 0/2/1, `--version`). Engine logic in one module; the CLI only translates. Make it runnable as `python /home/claude/cleanroom/impl/gpower_clone.py --test t-paired --mode ...` (a single entry script is fine; other modules next to it). Tests first: turn every row of the `Örnekler` tables in SPEC.md §3 and the t-paired public vectors in CONTRACT.md §9 into tests (expected values come from the tables; never compute them yourself), then write the engine. Tolerance: CONTRACT.md §6.

When done, run your tests and write /home/claude/cleanroom/impl/REPORT.md (in Turkish) with: how many SPEC rows and public vectors pass, every failing row with the reason (your bug vs. a gap in SPEC.md), every "SPEC'te yok" point you hit, and roughly how many iterations you needed. In your final message, give the pass counts, the list of SPEC gaps, and the exact command to run your CLI.
```
