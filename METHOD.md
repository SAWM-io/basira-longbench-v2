# Method — LongBench v2 pilot, Claude Opus 5.5 alone and with Basira memory

The pilot protocol below was written on 9 November 2026 **before any recall and any reading**, then amended after an
adversarial review of the harness, still before any recall and any scoring. A change made after reading the scores
would have been flagged as such and kept out of the main result; there was none. The last section (full run) was
added on the same day after the pilot's first scoring (29 questions) and changes no setting of the pilot. The 30th
question (the 16.2 M-character code repository) was scored after the other 29, once its writing into memory was
complete, with the same settings.

## Benchmark and official code

- **Dataset**: LongBench v2, `zai-org/LongBench-v2` on Hugging Face, revision
  `2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9` (last modified 20 December 2024), file `data.json`
  (SHA-256 `15d61c22d92c96900b3c4948b6aeea218d3214b676a65df48e7b8555604c7fe2`), Apache-2.0. 503 multiple-choice
  questions (A to D), in English, over six domains; length bands as defined by the authors (short, medium, long).
- **Official code**: `github.com/THUDM/LongBench`, commit `2e00731f8d0bff23dc4325161044d0ed8af94c1e`: `pred.py`,
  `result.py`, `prompts/0shot_cot.txt`, `prompts/0shot_cot_ans.txt`, `prompts/0shot_rag.txt`,
  `config/model2maxlen.json` (MIT).

## Sample

30 questions: 10 short, 10 medium, 10 long, drawn with `random.Random(20261109)`, under fixed constraints: the six
domains present, easy and hard questions in each length band, at least two texts longer than 4 M characters. The 30
questions are listed by their official `_id` in `results.json` and in `answers/`. The 30 texts are distinct
(55 k to 16.2 M characters, 38.8 M in total).

## Conditions (same 30 questions, same reader)

| Condition | What Claude Opus 5.5 reads at the first call |
|---|---|
| **A — Opus 5.5 alone** (`opus-5.5-alone_cot`) | the official `0shot_cot.txt` prompt with the WHOLE text, cut in the middle at **450,000 o200k tokens** if longer (rule of `pred.py`: the first and the last `max_len/2` tokens are kept) |
| **B — Opus 5.5 with Basira** (`opus-5.5-with-basira_rag-adaptive_cot`) | the passages recalled by Basira, put back in text order and presented as the official `--rag N --cot` path does: `0shot_rag.txt` template, `Retrieved chunk k: ...` |

For A and B alike, the second call is the official `0shot_cot_ans.txt` prompt, **without the text** ("The text is
too long and omitted here"), with the reasoning of the first call; the final answer is capped at 128 tokens; the
letter is extracted by `extract_answer` copied verbatim from `pred.py` (`The correct answer is \(([A-D])\)`, then
`The correct answer is ([A-D])`); an answer without a letter counts as wrong (`compensated = False`).

In B, as in `pred.py` when both `--rag` and `--cot` are set, the first call uses the RAG template, which asks for the
answer format directly instead of "Let's think step by step": this is why the `response_cot` field of B is often a
direct answer.

## Basira (condition B)

- **Memory**: one memory entity per text.
- **Writing**: the text is cut without loss into blocks of **at most 3,200 characters**, prefix included: a position
  tag `[[LB2 pos=NNNNN]]` followed by the piece of text, cut after a paragraph, a line, a sentence or a word. Each
  block is written as a message (`kind=message`, `role=user`) at its real sending time (never a backdated time). A
  block of this size is returned whole by recall. Writing goes batch by batch (at most 100 blocks), each batch
  after the previous one is done. For the one text longer than 5,000 blocks, the writing order is shuffled with a
  fixed seed. The pilot wrote 13,152 blocks.
- **Query**: the question, then the four choices `(A) ... (D)`.
- **Recall**: Basira's recall with `depth: "adaptive"`: Basira decides how many passages to return, **up to 320**.
  All pages of the answer are read. If the memory changes between two pages, the recall of the question is restarted
  (2 of the 30 recalls); the complete restarted recall is the one used.
- **Filtering, counted**: records not starting with a position tag (records derived by the memory itself, quoting a
  block after a short label, not text blocks) are set aside (36); passages whose `integrity_verified` is not true are
  set aside (0); a passage that differs from the block written is counted (0).
- **Budget**: if B's prompt exceeded 450,000 tokens or the reader's context budget, the passages ranked LOWEST by
  Basira would be removed first (end of the returned list), then the rest put back in text order, like an official
  top-N, instead of a middle cut. This never happened (0 passage removed).

## Reader

- One Claude Opus 5.5 agent (`claude-opus-5-5`, Claude Code sub-agent) **per question and per call**, no batching.
- Call 1 reads its prompt in parts of 12,000 o200k tokens with the Read tool (lines longer than 1,900 characters are
  wrapped); call 2 receives the official prompt without the text.
- **Context budget of A**: `max_len` is lowered in steps of 5% while the predicted peak context of the agent exceeds
  880,000 tokens, so that the context is never compacted. Effect in the pilot: two code repositories only, 450,000 →
  406,124 tokens and 385,816 tokens (instead of 441,553, a text that would not have been cut). If a compaction
  happened anyway, the task would be rejected and rerun with a `max_len` 15% lower.
- **Audit**: a task is invalid and rerun if its transcript shows a context compaction, a model other than
  `claude-opus-5-5`, a tool other than Read, a partial read (including a read truncated by the tool), a read missing,
  duplicated or outside the expected list, or a synthetic message (usage limit). An answer is kept only if the
  transcript of the agent that produced it passes the audit. Result: 120 tasks audited (30 questions × 2 conditions ×
  2 calls), 0 rejected.

## Keeping the answers away from the reader

The dataset file, which holds the answers, was kept unreadable from the first read on, except during scoring (the
first 29 questions were scored before the 30th was read with Basira). Recall queries and prompts were built from a
file holding the questions and choices only, without answers; the texts were read from copies under neutral file
names; and the transcript audit rejects any read outside the agent's own prompt files.

## Scoring and statistics

- `result.py` of the official repository, unchanged, on the two files of `answers/` (overall, easy, hard, short,
  medium, long). Main score on the valid answers (as `result.py` does), and a conservative score on 30 where a
  missing question counts as wrong: identical here (no missing question).
- Wilson 95% interval; paired comparison A/B with the exact McNemar test; number of answers without a letter.
- **Tokens read**: o200k tokens of the first-call prompt given to the reader (official template, question, choices
  and text): for A, `0shot_cot.txt` with the text after the middle cut; for B, `0shot_rag.txt` with the recalled
  passages. **Share read**: for A, tokens kept / tokens of the uncut prompt; for B, characters recalled / characters
  of the text. These per-question figures are taken from the run records and published in `results.json`; the
  repository alone does not allow recomputing them.
- **Passages from the removed middle** (texts cut for A only): a recalled passage is counted when it lies entirely
  in the part that the middle cut removes, estimated from character positions with the cut placed at `max_len/2`
  tokens from each end, in proportion to the token count of the text. It is an estimate.

## Deviations from the official protocol, declared in advance

1. Temperature cannot be set on Claude Opus 5.5 (official: 0.1). Opus always reasons: the "w/ CoT" protocol is used.
2. The official `max_new_tokens` (1,024 and 128) are replaced by a cap on the returned text, in o200k tokens,
   announced to the model. No first-call output reached 1,024 tokens; 12 final answers (6 per condition) were capped
   at 128 tokens, all after the answer letter.
3. The prompt is read in parts with the Read tool, inside a Claude Code agent (Claude Code system prompt).
4. Truncation at 450,000 o200k tokens for "Opus alone" (the official configuration uses 120,000, and 200,000 for
   Claude 3.5 Sonnet): the control is stronger than in the official protocol.
5. o200k counting (GPT-4o tokenizer) for every cut, as `pred.py` does for GPT models.

These scores are therefore **not comparable to the official leaderboard**, and no rank is claimed.

## Published answer files

`answers/*.jsonl` use the fields of the official `pred.py` output (`_id`, metadata, question, choices, `answer`,
`context`, `response_cot`, `response`, `pred`, `judge`), so that the official `result.py` scores them unchanged. In
both files, `context` holds the first 1,000 characters of the original LongBench v2 context. In a RAG run, `pred.py`
itself would store there the first 1,000 characters of the retrieved chunks; here the original text's first 1,000
characters are stored in both files (identical for all 30 questions).

## Full run (503 questions), in progress

Written on 9 November 2026 after the pilot's first scoring, before any reading of the full run. No setting changes.
One question outside the pilot (`66ead7bd5a08c7b9b35dca7a`) keeps a `max_len` of 354,000 tokens for "Opus alone",
fixed during the design study that preceded the pilot. The 503 questions are processed in 11 waves: wave 0 is the 30
pilot questions; the other 473 go into waves 1 to 10 of 47 to 48 questions, in a deterministic order (SHA-256 of the
seed and `_id`), stratified by length. One Basira memory per TEXT (462 distinct texts; 41 questions reuse a text already
written): a text is written once, in the first wave that needs it, and later questions recall it from the same memory.
Final score: all waves together (official `result.py`), paired comparison on the questions answered in both
conditions, and a conservative score on 503 where a missing question counts as wrong.
