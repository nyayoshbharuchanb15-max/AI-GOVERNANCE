# MCP Registry Publishing Guide

## Prerequisites

1. npm package published: `compliance-stack-mcp-server`
2. GitHub account with access to the repo

## Step 1: Install mcp-publisher

```bash
npm install -g @modelcontextprotocol/publisher
```

## Step 2: Login to GitHub

```bash
mcp-publisher login --github
```

This will open a browser for GitHub OAuth authentication.

## Step 3: Publish to Registry

```bash
mcp-publisher publish \
  --name compliance-stack \
  --description "17-phase compliance audit pipeline for AI models across EU AI Act, GDPR, NIST AI RMF, ISO 42001, and India DPDP Act. Zero data egress, W3C Verifiable Credentials." \
  --npm compliance-stack-mcp-server \
  --homepage https://github.com/nyayoshbharuchanb15-max/ComplianceStack \
  --repository https://github.com/nyayoshbharuchanb15-max/ComplianceStack
```

## Step 4: Verify

Visit https://registry.modelcontextprotocol.io to confirm the entry appears.

## Namespace Note

The registry validates namespace ownership. Since the npm package is `compliance-stack-mcp-server`, the registry entry will be:

```
compliance-stack
```

Or if using GitHub namespace:

```
io.github.nyayoshbharuchanb15-max/compliance-stack
```

## Troubleshooting

- If `mcp-publisher` fails, check that the npm package is publicly accessible
- Ensure the GitHub repo is public
- Check the registry FAQ at https://github.com/modelcontextprotocol/registry
