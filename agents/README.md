# ADW Agent Run Artifacts

This directory contains output artifacts from the AI Developer Workflow (ADW) system — a self-building pipeline that reads GitHub issues and autonomously plans, implements, commits, and opens pull requests using Claude Code.

## What's in here

Each subdirectory is named by its 8-character ADW run ID and contains the raw output from each agent in the pipeline:

```
agents/
└── 68c4cc48/                          ← run ID (portfolio example)
    ├── issue_classifier/              ← classified issue as /feature, /bug, or /chore
    ├── branch_generator/              ← generated the git branch name
    ├── sdlc_planner/                  ← wrote the implementation spec
    ├── sdlc_planner_committer/        ← committed the spec to the branch
    ├── sdlc_implementor/              ← read the spec and edited main.py
    ├── sdlc_implementor_committer/    ← committed the code changes
    └── pr_creator/                    ← opened the pull request on GitHub
```

Each agent folder contains:
- `prompts/` — the exact slash command prompt sent to Claude Code
- `raw_output.jsonl` — streaming JSON output from Claude Code CLI
- `raw_output.json` — same output parsed into a JSON array for readability

## Preserved example: `68c4cc48`

This run processed GitHub issue #4 ("Add /schema endpoint to expose database structure") and produced PR #7, which added `GET /schema` to `main.py` and updated `API_DOCUMENTATION.md`.

Future runs are excluded via `.gitignore` to prevent repo bloat. Re-run the workflow to generate fresh examples:

```bash
uv run adws/adw_plan_build.py <issue_number>
```
