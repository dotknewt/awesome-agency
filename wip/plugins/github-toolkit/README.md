# github-toolkit

Scaffold GitHub repo metadata — issue templates and CI workflows — plus the
`branch-warden` agent for branch prep/cleanup and the `issue-filer` agent for
lightweight issue creation.

Components (shared pools in this repo):
- Skills: [`github-scaffold`](../../skills/github-scaffold), [`github-workflow`](../../skills/github-workflow)
- Agents: [`branch-warden`](../../agents/branch-warden), [`issue-filer`](../../agents/issue-filer)
- Commands: `/github-scaffold`, `/create-issue-template`, `/scaffold-ci-workflow`
- Instructions: [`instructions/`](../../instructions)

Install: `claude plugin install github-toolkit@awesome-agency`
