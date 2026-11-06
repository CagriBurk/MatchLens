@.agents/AGENTS.md

At the start of a new session, read docs/07_session_handoff.md before doing anything else.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- graphify-out/ is gitignored and local; rebuild it with the command above. If it is missing, run `graphify extract . --code-only`.

Limits of this graph:
- It is code-only. Decisions and plans are not in it; read docs/03_roadmap.md and docs/06_master_architecture_and_audit.md for those.
- Calls made from module-level code are not recorded, only imports. This covers ui/app.py, ui/pages/*, scripts/research/twin_lab.py. `graphify affected` can therefore miss callers, so confirm with grep before renaming a symbol or changing its signature.
- Names such as run() and market_probs() exist in several files. When a query exits with code 3, retry with `<path>::<symbol>` or the listed node id.
