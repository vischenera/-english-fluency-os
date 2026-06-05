# Review Protocol

Fluency comes from *re-meeting* cards until retrieval is instant — not from seeing each card once. This protocol gives you a concrete spaced-repetition rhythm, a weekly recording loop, and an optional AI feedback loop.

## Spaced Repetition (Leitner Ladder)

Keep cards in five boxes. A card moves up a box each time you can start a correct sentence with it within 3 seconds. If you hesitate or get it wrong, it drops back to Box 1.

| Box | Review every | Meaning |
|---|---|---|
| 1 | every day | new or recently failed |
| 2 | every 3 days | starting to stick |
| 3 | every 7 days | mostly automatic |
| 4 | every 14 days | nearly owned |
| 5 | "warm" — once a month | owned; just keep it alive |

Rules:
- A card is **graduated** only after 3 instant, correct retrievals in a row.
- Only ~5–8 cards should be in Box 1 at a time. Don't add new cards while Box 1 is full.
- Recognition does not count. If you can only *recognise* it, it stays in Box 1.

A simple paper version: five columns; move a tally mark right on success, back to column 1 on a miss.

## Daily Micro-Review

Before any new cards, retrieve yesterday's Box 1 cards aloud. This is the first minute of the daily protocol.

## Weekly Review

1. Record a 60-second answer to one prompt from `daily/prompt_bank.md`.
2. Count silent pauses longer than 2 seconds.
3. Note your **longest fluent run** (seconds without a >2s pause).
4. Note up to 3 repeated errors — then pick **only one** to target next week.
5. Save one sentence you said well; reuse it.

## Monthly Review

Re-record the same prompt you used four weeks ago and compare:

- Did sentence starts get faster?
- Did pauses drop / did the longest fluent run get longer?
- Did the same grammar errors repeat less?
- Is pronunciation clearer on your target sounds?
- Can you speak longer without panic?

## Optional: AI Feedback Loop

This turns the static curriculum into a feedback engine using the corrections deck.

1. Record your 60-second answer and get a transcript (any speech-to-text, or type out what you said).
2. Paste the transcript to an AI assistant with this prompt:
   > "I'm a Malayalam-speaking English learner. Here is a transcript of me speaking. Using common Indian/Malayalam-English transfer errors, point out: (1) any error patterns you see, (2) my top 3 errors to fix first, and (3) a more natural version of 2–3 sentences. Be concise."
3. Match the feedback against `curriculum/corrections/common_corrections.md`. Put each flagged pattern into Box 1.
4. Target one pattern for the week. Re-record at week's end and check if it dropped.

Do this once a week at most — the daily loop stays offline and short.
