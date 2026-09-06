# Agent evaluations

This suite checks the agent behavior against real OpenAI responses. It is kept
outside `tests/` because it consumes tokens and is not a deterministic unit
test suite.

## Run

Activate the virtual environment and configure the same environment variables
used by the application: `OPENAI_API_KEY`, `SEED_USER_PASSWORD`, and
`JWT_SECRET`. `OPENAI_MODEL` is optional and defaults to `gpt-5.6-terra`.

Run the suite from the repository root:

```bash
python -m evals.run
```

Each case uses its own in-memory SQLite database. Setup bookings are created
directly through `BookingService`, so the behavior being measured is the agent
decision and not its ability to prepare the test data.

## Reading the result

The runner prints one symbol per case, the model used, and a final result in
`N/M passed` format. For a failed case, it also prints the last assistant
response so the tool-call failure can be understood in context. It exits with a
non-zero code when at least one case fails.

LLM results are not deterministic. The same case can pass in one run and fail
in the next one, even with the same model and input. A run should be read as a
proportion and repeated when comparing prompt changes, not treated as a final
binary answer.

## Model comparison

I ran the current 16-case suite three times with each model. I counted only
runs that printed every case and the final summary.

| Model | Complete runs | Results | Total |
|---|---:|---|---:|
| `gpt-5.6-terra` | 3 | 16/16, 16/16, 16/16 | 48/48 (100%) |
| `gpt-4o-mini` | 3 | 15/16, 15/16, 15/16 | 45/48 (93.8%) |


I selected Terra for the demo because it was more consistent in these runs.
The trade-off is cost. As of 2026-09-05, the official prices per one million
text tokens are:

| Model | Input | Output |
|---|---:|---:|
| `gpt-5.6-terra` | $2.00 | $12.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |

Terra is about 13 times more expensive for input and 20 times more expensive
for output. This is acceptable for a low-volume demo, but I would measure the
quality and cost again before using it for a production workload. The model
remains configurable through `OPENAI_MODEL`.

Sources: [GPT-5.6 Terra pricing](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
and [GPT-4o mini pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini).
