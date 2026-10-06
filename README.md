# Neuro-Symbolic Deterministic AI Hallucination Detector — Mid-Sem Prototype

This prototype separates **AI generation** from **deterministic verification**.

## Run

```bash
python src/main.py
```

Then open `report.html`.

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Where to change the experiment

### Trusted source
Edit:

`ground_truth.txt`

These facts define what the verifier is allowed to treat as source truth.

### AI output
Edit:

`ai_response.txt`

Each non-empty line is treated as one simulated LLM-generated claim. Change these lines and rerun `python src/main.py` to see the verdicts change.

The current file intentionally contains supported claims, unsupported claims, a contradiction, an unknown entity, and a multi-hop derived claim.

## Mathematical core

The source becomes a labeled directed graph:

`G = (V, E, P)`

For predicate `p`, the system constructs a binary adjacency matrix `A_p`.

Direct verification checks whether:

`A_p[i,j] = 1`

Explicit multi-hop rules use Boolean matrix composition. For example:

`CONTROLS(x,y) AND ACTIVATES(y,z) -> INFLUENCES(x,z)`

is evaluated using:

`A_CONTROLS ⊙ A_ACTIVATES`

An arbitrary path is never automatically treated as proof.

## Verdicts

- **VERIFIED** — directly supported by a source edge or explicit rule.
- **CONTRADICTED** — the source explicitly contains the opposite relation.
- **UNSUPPORTED** — entities exist, but no declared fact/rule supports the claim.
- **UNRESOLVED** — one or more claimed entities cannot be resolved to the source graph.

For this prototype, `CONTRADICTED` and `UNSUPPORTED` are reported as **hallucination candidates**, while `UNRESOLVED` is kept separate because it may be an entity-resolution failure rather than a factual hallucination.

## Next research stage

Replace `ai_response.txt` with real LLM adapters (GPT/Gemini/Claude/local models) while keeping the same deterministic verifier. Then compare hallucination rates across models using the same source documents and benchmark claims.
