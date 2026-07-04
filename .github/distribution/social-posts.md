# Reddit/HN Post Drafts

## r/mcp Post

**Title:** ComplianceStack — Open-source MCP server for EU AI Act / GDPR compliance audits (17 tools, zero data egress)

**Body:**

Hey r/mcp,

I've been building an MCP server that runs automated compliance audits against AI models. It checks adherence to 5 regulatory frameworks (EU AI Act, GDPR, NIST AI RMF, ISO 42001, India DPDP Act) through a 17-phase audit pipeline.

**What it does:**

- Risk classification (EU AI Act Art. 6)
- Bias assessment with Fairlearn metrics
- DPIA generation (GDPR Art. 35)
- ROPA generation (GDPR Art. 30)
- Adversarial robustness testing (prompt injection, jailbreak, OOD, model inversion)
- Drift detection with auto re-audit
- Human oversight verification (BLOCKER FAIL if missing)
- Agent trust and tool permission audits
- W3C Verifiable Credential certificates (Ed25519-signed)

**Key design decisions:**

- Zero data egress by default — all operations run in-process
- 3 transport modes: stdio, SSE, Streamable HTTP
- BLOCKER FAIL mechanism prevents certification of non-compliant models
- 244 passing tests across TypeScript and Python backends

**Install:**

```bash
npx compliance-stack-mcp-server
```

Or add to Claude Desktop config:

```json
{
  "mcpServers": {
    "compliance-stack": {
      "command": "npx",
      "args": ["compliance-stack-mcp-server"]
    }
  }
}
```

Would love feedback on the architecture and any gaps in the regulatory coverage.

[GitHub](https://github.com/nyayoshbharuchanb15-max/ComplianceStack) | [npm](https://www.npmjs.com/package/compliance-stack-mcp-server)

---

## r/ClaudeAI Post

**Title:** I built an MCP server that audits AI models against the EU AI Act and GDPR — 17 compliance checks in your IDE

**Body:**

With the EU AI Act now in force, I needed a way to audit AI models for compliance without sending data to external services. So I built ComplianceStack — an MCP server that runs a 17-phase compliance pipeline entirely on-premise.

**What you can ask Claude to do:**

- "Classify model X against EU AI Act risk tiers"
- "Run a bias assessment on model X"
- "Generate a DPIA for model X"
- "Run adversarial tests on model X"
- "Generate a W3C compliance certificate for model X"

**The pipeline covers:**

- EU AI Act (risk classification, human oversight, bias, adversarial robustness)
- GDPR (DPIA, ROPA, DSAR, cross-border transfers)
- NIST AI RMF, ISO 42001, India DPDP Act

Everything runs locally. No data leaves your machine unless you explicitly configure an external endpoint for adversarial testing.

```json
{
  "mcpServers": {
    "compliance-stack": {
      "command": "npx",
      "args": ["compliance-stack-mcp-server"]
    }
  }
}
```

[GitHub](https://github.com/nyayoshbharuchanb15-max/ComplianceStack)

---

## r/artificial Post

**Title:** Open-source MCP server for AI governance — audits models against EU AI Act, GDPR, NIST, ISO 42001

**Body:**

With AI regulation accelerating globally, I built an open-source tool that automates compliance auditing for AI systems.

ComplianceStack is an MCP server that runs a 17-phase audit pipeline checking adherence to:

- **EU AI Act** — Risk classification, human oversight, bias, adversarial robustness
- **GDPR** — DPIA, ROPA, DSAR, cross-border transfers
- **NIST AI RMF** — Risk mapping, governance, measurement
- **ISO/IEC 42001:2023** — AIMS compliance
- **India DPDP Act** — Consent, fiduciary duties

**Key features:**

- Zero data egress by default (all on-premise)
- W3C Verifiable Credential certificates (cryptographically signed)
- BLOCKER FAIL mechanism prevents certification of non-compliant models
- 244 passing tests

It works with Claude Desktop, Cursor, Windsurf, or any MCP-compatible client.

[GitHub](https://github.com/nyayoshbharuchanb15-max/ComplianceStack)

---

## Hacker News (Show HN)

**Title:** Show HN: ComplianceStack – Open-source MCP server for EU AI Act / GDPR compliance audits

**Body:**

I built an MCP server that runs automated compliance audits against AI models. It checks adherence to 5 regulatory frameworks (EU AI Act, GDPR, NIST AI RMF, ISO 42001, India DPDP Act) through a 17-phase audit pipeline.

Key design decisions:

- Zero data egress by default — all audits run in-process
- BLOCKER FAIL mechanism prevents certification of non-compliant models
- W3C Verifiable Credentials for cryptographically signed audit certificates
- 3 transport modes: stdio, SSE, Streamable HTTP

The server exposes 17 tools covering risk classification, bias assessment, DPIA generation, adversarial testing, drift detection, and more.

Install: `npx compliance-stack-mcp-server`

GitHub: https://github.com/nyayoshbharuchanb15-max/ComplianceStack
