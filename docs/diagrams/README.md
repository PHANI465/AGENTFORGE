# Architecture Diagrams

Rendered as [Mermaid](https://mermaid.js.org/) — GitHub renders these natively, no
extra tooling needed to view them in the repo.

- [`architecture.md`](architecture.md) — system components and how they talk to each other
- [`request-flow.md`](request-flow.md) — sequence diagram of a single agent run, start to finish
- [`data-model.md`](data-model.md) — entity-relationship diagram of the 9 Postgres tables

These reflect the actual code (`packages/common/agentforge_common/orm.py`,
`services/*/main.py`), not the original design in `ARCHITECTURE.md` — check
here first if the two ever disagree.
