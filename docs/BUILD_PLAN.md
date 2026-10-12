# RepoArena — build plan

An original open-source model harness for comparing solutions to engineering issues.

## Registration status

The organizer requested a public `Team Registration: <Team Name>` issue before coding. GitHub API access was unavailable during the build, and the participant details were not supplied. Implementation proceeded after the user explicitly asked to build immediately. Complete registration with the actual details and timeline; do not imply the issue predates implementation. Share only contact information intended for public disclosure.

## Demo scope

Paste an engineering issue and optional repository context. A Builder proposes a solution, a Skeptic critiques it, and a Judge evaluates the proposal against correctness, security, and testability. Show each stage and export the complete session as JSON.

Use an Ollama-compatible open-weight model selected by the user. Keep a clearly labeled sample replay available for presentations without a running model. A replay is not a live inference result.

## Task issues

1. Implement the original harness, structured outputs, timeout handling, and model adapter.
2. Build the arena interface with stage progress, rubric scores, and JSON export.
3. Add meaningful tests for parsing, scoring, provider errors, and the complete simulated workflow.
4. Document model installation, live inference, sample replay, limitations, and demo steps.

Create one issue per task, assign it, and work on issue branches. Open draft PRs early. Link actual issue numbers after creation; do not invent issue references.

## Technical direction

Python HTTP backend and a vanilla HTML/CSS/JavaScript interface minimize installation requirements. Bind to loopback by default. Use server-side requests to Ollama. Treat model responses and pasted context as untrusted data. Do not execute generated code. Bound request sizes and timeouts.

## Acceptance checks

- A sample session completes and is visibly marked as sample data.
- Live mode reports unavailable Ollama cleanly and never silently substitutes sample results.
- Tests cover the harness and malformed model responses.
- A functional HTTP request exercises the backend and serves the interface.
- README and open-source license accompany the implementation.

## Presentation

Explain the issue, run the arena, inspect the critique and rubric, and export the evidence. State which model was used and whether the session was live or a sample replay. Do not describe model-judged scores as proof that a solution is correct.
