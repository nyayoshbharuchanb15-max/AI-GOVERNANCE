# ComplianceStack — Distribution & Community Submission Guide

## Quick Reference

| Target | Type | Priority | Status |
|--------|------|----------|--------|
| npm publish | Package registry | P0 | Ready (needs `npm login`) |
| MCP Registry | Official registry | P0 | Ready (needs npm first) |
| wong2/awesome-mcp-servers | Curated list | P1 | PR draft ready |
| appcypher/awesome-mcp-servers | Curated list | P1 | PR draft ready |
| TensorBlock/awesome-mcp-servers | Curated list | P1 | PR draft ready |
| Vaquill-AI/awesome-legaltech | Legal tech list | P1 | PR draft ready |
| ICTRecht/Legal-GenAI-Resources | Legal AI list | P2 | PR draft ready |
| r/mcp | Reddit | P2 | Post draft ready |
| r/ClaudeAI | Reddit | P2 | Post draft ready |
| r/artificial | Reddit | P3 | Post draft ready |
| Hacker News | Show HN | P3 | Post draft ready |

## Step 1: Publish to npm

```bash
cd mcp-server
npm login
npm publish
```

## Step 2: Register on MCP Registry

```bash
# Install mcp-publisher
npm install -g @modelcontextprotocol/publisher

# Login and publish
mcp-publisher login --github
mcp-publisher publish --name compliance-stack --version 3.1.0
```

## Step 3: Submit PRs

See individual files in this directory for each target.
