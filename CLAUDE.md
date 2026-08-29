# datacluster-template — Claude Code reference

## Forge access, the sandbox, and landing work

Auto-loaded, so the things an agent must not miss live here rather than in
`AGENTS.md` (which is *not* auto-loaded unless imported).

**Network calls are sandboxed unless escalated.** `gh`, `fj`, `curl`, `kubectl`
and `git push/fetch/pull` return **exit 0 with empty output and no error** inside
the agent tool sandbox. An unreachable call and a genuinely empty result look
identical. Escalate the sandbox on every such call (Claude Code: the Bash
parameter `dangerouslyDisableSandbox: true`). That is an autonomous action, never
a request to the owner. **Never conclude absence from a sandboxed result** — if a
probe could not run, the finding is *could not check*, not *none found*.

**Standard workflow does not need permission.** Advancing `main` — commit, push,
PR create, PR merge, release cut, deploy — is routine, as are minting and
reviewing. This repo declares any exceptions in `.claude/gates.json`; **absence of
a declaration means routine**, never the reverse.

**Credentials already exist.** GitHub via `gh` (token in the system *keyring*, not
`~/.config/gh/hosts.yml`); Forgejo via `fj` (`fj auth list`) plus
`~/.config/forgejo/workstation-scope-token`. `git push` needs no token handling —
`~/.gitconfig` wires helpers for both forges. Check a credential’s audience before
using it.

**Land the work.** A stable diff is not done. Merge to `main` (or the main
development branch where `main` is protected) and let CI there catch what
targeted checks did not. Open a PR only for a named action: an operator handoff, a
dispatched review, or a CI check that runs nowhere else. `origin` is not reliably
canonical — check `git config claude.canonicalRemote`.
