# Submission preparation

## Project description

RepoArena is an original open-source model harness that turns an engineering issue into an inspectable debate. Two independently prompted builders propose different solutions. A skeptic identifies failure modes and tests, then a judge scores both proposals. The harness validates structured output, calculates the weighted verdict, streams progress to a browser, and exports every prompt and response. Live inference uses an open-weight model through Ollama.

## Why it fits the challenge

- Original harness implementation: stage orchestration, response validation, explicit role context, deterministic score aggregation, and evidence export.
- Open-weight AI performs the core work for new challenges.
- Application code is MIT licensed.
- A public GitHub repository is required; verify its visibility before submitting.
- This is a model harness and app, not an agent-skill submission.

## Before submitting

- [ ] Make the repository public and verify that its default branch shows the project.
- [ ] Complete the organizer's registration issue with your actual team details.
- [ ] Record the selected model name and check its weight license.
- [ ] Complete a real live Ollama run and export its session.
- [ ] Capture a short demo showing the issue, debate, verdict, and evidence export.
- [ ] Include the GitHub URL, demo evidence, setup instructions, and team information in the submission form.
- [ ] Keep real issues, commits, PRs, and reviews visible; do not invent earlier collaboration history.

## Validation in the build environment

The automated suite exercises the harness and HTTP server, including an Ollama-protocol simulation. Browser checks exercise sample replay and export. These checks do not establish that a real model has run. A live inference session must be checked on the machine hosting Ollama before claiming model performance in the submission.

## Suggested short pitch

“AI gives us answers faster than we can review them. RepoArena makes the review visible: two solutions, an adversarial critique, a transparent rubric, and a complete evidence trail. It runs on an open-weight model with Ollama and needs no application dependencies.”
