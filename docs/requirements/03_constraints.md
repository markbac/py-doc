---
title: Constraints
---

# Constraints

| ID | Constraint | Why |
|---|---|---|
| CON-01 | Pandoc writes every Word, PowerPoint, PDF, HTML and site page. py-doc has no renderer of its own. | One mature converter instead of several partial ones. The earlier native renderers were removed |
| CON-02 | Tools that are not Python run in a Docker container. On Windows, Docker Engine runs in a WSL 2 distribution, not Docker Desktop. | Identical tools on every machine and in CI, nothing to install but Python and Docker, and no Docker Desktop licence |
| CON-03 | Linux and Windows only. | The tool runner depends on Docker on Linux and on WSL on Windows. macOS is not tested |
| CON-04 | Python 3.10 or later. | The language features and libraries py-doc uses |
| CON-05 | Structurizr DSL is read by structurizr-cli, and views are drawn by Structurizr Local. | No second DSL parser, and pictures look as the team sees them in Structurizr |
| CON-06 | Manual Structurizr layouts are stored in `workspace.json` beside the DSL. | The DSL has no syntax for element positions. Structurizr Local merges the two when it reads the DSL |
| CON-07 | py-doc orchestrates MkDocs and Starlight and never replaces their configuration. | Sites keep their themes, plugins and hand-made pages |
| CON-08 | The linter parses Markdown with markdown-it-py, separately from pandoc. | It needs line numbers and the exact source text, which pandoc's tree does not give |
| CON-09 | MIT licence. | |
