# copy/add skill,agent,instruction,plugin etc from source
- When instructed to add/copy an extension and given a source (github repo, marketplace etc), do not install it, but rather add it as if project root was the custom configs directory (like .claude/, .github/ etc)
# conventions
- default branch name when creating repositories is "main"
- default to delegating todo writing to small, fast, cheap model subagent

# steward
- additional command that performs instructions-audit only adding changes that surfaced in the last 5 commits
- Extend the steward plugin to also maintain tests

# contract ownership
- Should we have a contract owner; something(skill,agent) that owns contracts where contracts are needed (schema, tests .. ?)

# docker-toolkit
- Evaluate gains if modifying docker-toolkit to smaller components
  - an agent specialized in mcp conversion
  - a skill for converting a non-docker mcp server to docker mcp

## deferred
- scripts/build-and-register.sh
  - automate build + catalog registration + secret set for the `dockerize-mcp-server` skill (roadmapped for v2)
