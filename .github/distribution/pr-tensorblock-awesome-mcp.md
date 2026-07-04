# PR: TensorBlock/awesome-mcp-servers

## Category

Add under: `### Governance & Compliance` or `### Regulatory & Legal`

## PR Title

`feat: add ComplianceStack — 17-tool EU AI Act / GDPR compliance audit server`

## PR Body

```markdown
### What

[ComplianceStack](https://github.com/nyayoshbharuchanb15-max/ComplianceStack) is an enterprise-grade MCP server that runs a 17-phase compliance audit pipeline against AI models, checking adherence to 5 regulatory frameworks:

- **EU AI Act** (Reg. 2024/1689)
- **GDPR** (Reg. 2016/679)
- **NIST AI RMF** (AI 100-1)
- **ISO/IEC 42001:2023**
- **India DPDP Act 2023**

### Why it's useful

- **17 MCP tools** covering risk classification, bias assessment, DPIA generation, adversarial testing, drift detection, agent trust audits, and more
- **Zero data egress** — all audits run on-premise by default
- **W3C Verifiable Credentials** — cryptographically signed audit certificates
- **BLOCKER FAIL mechanism** — prevents certification of non-compliant models
- **3 transport modes** — stdio, SSE, Streamable HTTP

### Install

```bash
npx compliance-stack-mcp-server
```

Or via Docker:

```bash
docker compose up --build -d
```

### Links

- [GitHub](https://github.com/nyayoshbharuchanb15-max/ComplianceStack)
- [npm](https://www.npmjs.com/package/compliance-stack-mcp-server)
```

## Entry for catalog.json

```json
{
  "name": "ComplianceStack",
  "description": "17-phase compliance audit pipeline for AI models across EU AI Act, GDPR, NIST AI RMF, ISO 42001, and India DPDP Act. Zero data egress, W3C Verifiable Credentials.",
  "url": "https://github.com/nyayoshbharuchanb15-max/ComplianceStack",
  "npm": "compliance-stack-mcp-server",
  "transport": ["stdio", "sse", "streamable-http"],
  "tags": ["compliance", "governance", "eu-ai-act", "gdpr", "audit", "bias", "dpia"]
}
```

## Checklist

- [ ] Fork the repo
- [ ] Add entry to `data/catalog.json` if they have one
- [ ] Add markdown entry under relevant category
- [ ] Open PR with descriptive title
