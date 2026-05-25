Use the current coding environment's configured model to propose reusable project knowledge from
this chat/session. CodingScaffold itself does not call a model; this command is agent-side help for
not forgetting useful lessons.

Do not write raw chat transcripts into team knowledge.

1. Inspect the active task, recent decisions, verification results, and any session trace under
   `.coding-scaffold/sessions/`.
2. Extract only durable candidates:
   - project facts
   - team preferences
   - accepted or rejected decisions
   - failed attempts and why they failed
   - useful commands or gotchas
   - reusable prompts, skills, or agent patterns
3. Exclude secrets, credentials, personal data, private customer data, irrelevant conversation, and
   speculation that was not verified.
4. Prefer adding concise bullets to `## Reusable Knowledge Discovered` in the active session trace.
5. If asked to write files, create reviewable proposals only:
   - `.coding-scaffold/knowledge/wiki/<slug>.md.new` for durable wiki candidates
   - `.coding-scaffold/knowledge/decisions/<slug>.md.new` for decision candidates
   - `.coding-scaffold/memory/session_lesson/<date>-<slug>.md` for short-lived lessons
   - `.coding-scaffold/memory/failed_attempt/<date>-<slug>.md` for failed attempts
6. Include `scope`, `maturity: draft`, `owner`, `last_reviewed`, and `source_refs` frontmatter when
   writing knowledge proposals.
7. End with a short list of proposed knowledge candidates and say which files, if any, were written.
