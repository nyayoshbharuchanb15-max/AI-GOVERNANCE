// SPDX-License-Identifier: Apache-2.0
// Governance tools — MCP-layer validation + authorization gate tests (no network).
import { describe, it, expect } from "vitest";
import {
  GOVERNANCE_TOOL_SCHEMAS,
  isGovernanceTool,
  governanceToolScope,
  validateGovernanceInput,
} from "../governance-tools.js";
import { assertScope, canonicalJson, GovernanceAuthzError } from "../governance-client.js";

function fakeJwt(payload: Record<string, unknown>): string {
  const b64 = (obj: unknown) => Buffer.from(JSON.stringify(obj)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(payload)}.signature`;
}

describe("governance tool registry", () => {
  it("exposes 9 phase tools + reaudit + run status", () => {
    expect(GOVERNANCE_TOOL_SCHEMAS.length).toBe(11);
    const names = GOVERNANCE_TOOL_SCHEMAS.map((t) => t.name);
    for (const expected of [
      "intake_register", "map_regulatory_scope", "classify_risk",
      "check_data_protection", "evaluate_fairness", "test_robustness",
      "verify_explainability", "assemble_certification", "configure_monitoring",
      "trigger_reaudit", "get_audit_run",
    ]) {
      expect(names).toContain(expected);
    }
  });

  it("every governance tool schema forbids additional properties", () => {
    for (const tool of GOVERNANCE_TOOL_SCHEMAS) {
      expect((tool.inputSchema as { additionalProperties?: boolean }).additionalProperties).toBe(false);
    }
  });

  it("maps each phase tool to a least-privilege scope", () => {
    expect(governanceToolScope("intake_register")).toBe("phase:intake");
    expect(governanceToolScope("classify_risk")).toBe("phase:risk");
    expect(governanceToolScope("assemble_certification")).toBe("phase:certify");
    expect(governanceToolScope("trigger_reaudit")).toBe("reaudit:trigger");
    expect(isGovernanceTool("classify_ai_risk")).toBe(false); // legacy suite untouched
  });
});

describe("MCP-layer schema validation (rejects before FastAPI)", () => {
  it("rejects malformed intake (missing modelVersion)", () => {
    const result = validateGovernanceInput("intake_register", { modelId: "m1" });
    expect(result.valid).toBe(false);
  });

  it("rejects unknown extra fields", () => {
    const result = validateGovernanceInput("map_regulatory_scope", {
      runId: "12345678-abcd", evil: true,
    });
    expect(result.valid).toBe(false);
  });

  it("rejects invalid enum values", () => {
    const result = validateGovernanceInput("test_robustness", {
      runId: "12345678-abcd", testSuites: ["nuclear_launch"],
    });
    expect(result.valid).toBe(false);
  });

  it("accepts a valid classify_risk payload", () => {
    const result = validateGovernanceInput("classify_risk", {
      runId: "12345678-abcd",
      riskInputs: { annexIIICategories: ["employment"], interactsWithHumans: true },
    });
    expect(result.valid).toBe(true);
  });
});

describe("MCP-layer authorization gate (before FastAPI)", () => {
  it("rejects tokens lacking the required scope", () => {
    const token = fakeJwt({ role: "intake-officer", scopes: ["phase:intake", "runs:read"] });
    expect(() => assertScope(token, "phase:certify")).toThrow(GovernanceAuthzError);
  });

  it("allows tokens holding the required scope", () => {
    const token = fakeJwt({ role: "governance-admin", scopes: ["phase:certify"] });
    expect(() => assertScope(token, "phase:certify")).not.toThrow();
  });
});

describe("canonical JSON request hashing", () => {
  it("is key-order independent and matches the Python canonical form", () => {
    const a = canonicalJson({ b: 1, a: { d: [1, 2], c: "x" } });
    const b = canonicalJson({ a: { c: "x", d: [1, 2] }, b: 1 });
    expect(a).toBe(b);
    expect(a).toBe('{"a":{"c":"x","d":[1,2]},"b":1}');
  });
});
