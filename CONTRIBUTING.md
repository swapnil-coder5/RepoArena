# Contributing

1. Open a task issue describing the user-facing result and how it will be tested.
2. Create a feature branch; do not push changes directly to `main`.
3. Make focused commits that reference the real issue number.
4. Open a draft PR early. Include the problem, change, and verification. Use `Closes #N` only for an actual issue.
5. Run `python -m unittest discover -s tests -v` and `node --check web/app.js`.
6. Ask another teammate for review when possible.

Keep the app dependency-light. Changes to model prompts or score validation should include tests for their failure paths. Never commit credentials, private repository context, or session exports containing sensitive data.

The event's team-registration issue requires personal details. Participants should enter those themselves and include only information they intend to publish.
