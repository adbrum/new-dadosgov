---
name: promote
description: Open the promotion PR for the next environment (develop → tst → ppr → main) in one of the dadosgov repos
---

Arguments: $ARGUMENTS — expected `<backend|frontend> <tst|ppr|main>`.

Delegate to the `promoter` agent. If an argument is missing, first show what is pending in
both repos (`git log --oneline origin/<base>..origin/<head>` for each hop) and ask which
promotion to open.

Steps the agent must follow:

1. `git -C <dir> fetch origin`
2. List the commits that would be promoted: `git -C <dir> log --oneline origin/<target>..origin/<source>` where `<source>` is the environment immediately below `<target>`.
3. Show that list to the user and get a yes before opening anything.
4. `gh pr create --repo amagovpt/<repo> --base <target> --head <source> --title "chore(promote): <source> -> <target>" --body "<what is being promoted, ticket keys, how to verify in <target>, deploy order if the other repo also changed>"`
5. Report the PR URL and the CI status. Never merge.
