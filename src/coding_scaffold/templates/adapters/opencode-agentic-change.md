Run a small agentic coding loop.

1. Use the explorer agent to inspect the relevant files and confirm the smallest safe scope.
2. Use the implementer agent to make only that change.
3. Run the narrowest meaningful verification.
4. Use the reviewer agent to look for regressions, missing tests, and unclear behavior.
5. Run a knowledge nudge: identify durable lessons worth remembering and add candidates to the
   active session trace under `## Reusable Knowledge Discovered`.
6. Summarize changed files, checks, review findings, knowledge candidates, and any follow-up.
