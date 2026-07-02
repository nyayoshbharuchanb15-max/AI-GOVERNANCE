"""
Tests: ROPA Generation (GDPR Art. 30) — Record of Processing Activities
"""

from __future__ import annotations
import uuid

import pytest
from models.schemas import (
    GenerateROPARequest,
    ROPAReport,
    ROPADataSubjectCategory,
    ROPADataCategory,
)
from routers.ropa import generate_ropa


class TestGenerateROPARequestValidation:
    def test_minimal_request(self):
        req = GenerateROPARequest(
            modelId="test-model",
            controllerName="Acme Corp",
            controllerAddress="123 Main St",
            controllerEmail="dpo@acme.com",
            processingPurposes=["Model training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="employees",
                    description="Current and former employees",
                    retentionPeriod="3 years",
                    erasureMechanism="Automated delete after notice period",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="performance_data",
                    description="Model performance metrics",
                    retentionPeriod="5 years",
                    erasureMechanism="Archived then deleted",
                    securityMeasures=["Encryption at rest"],
                )
            ],
            recipientCategories=["Cloud provider"],
        )
        assert req.modelId == "test-model"
        assert len(req.dataCategories) == 1

    def test_full_request(self):
        req = GenerateROPARequest(
            modelId="test-model",
            controllerName="Acme Corp",
            controllerRepresentative="Jane Doe",
            dpoName="John Smith",
            controllerAddress="123 Main St, London, UK",
            controllerEmail="dpo@acme.com",
            jointControllers=["Partner Ltd"],
            processingPurposes=["Model training", "Inference serving"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="customers",
                    description="End users of the AI system",
                    retentionPeriod="5 years",
                    erasureMechanism="Right to erasure via portal",
                ),
            ],
            dataCategories=[
                ROPADataCategory(
                    category="biometric_data",
                    description="Facial recognition data",
                    specialCategory=True,
                    retentionPeriod="2 years",
                    erasureMechanism="Anonymized after 2 years",
                    securityMeasures=["Encryption", "Access control", "Audit logging"],
                ),
            ],
            recipientCategories=["AWS", "Auth0"],
            crossBorderTransfer=True,
            thirdCountries=["United States"],
            transferSafeguards=["SCCs", "DPA in place"],
            retentionScheduleDescription="Retention per data category policy",
            securityMeasures=["Encryption at rest", "TLS 1.3", "RBAC"],
        )
        assert req.dpoName == "John Smith"
        assert len(req.securityMeasures) == 3
        assert req.crossBorderTransfer is True

    def test_special_category_flag(self):
        cat = ROPADataCategory(
            category="health_data",
            description="Medical records",
            specialCategory=True,
            retentionPeriod="10 years",
            erasureMechanism="Archived then destroyed",
            securityMeasures=["Encryption"],
        )
        assert cat.specialCategory is True


class TestROPADataSubjectCategory:
    def test_create_subject_category(self):
        cat = ROPADataSubjectCategory(
            category="children",
            description="Minors under 16",
            retentionPeriod="Until age 18",
            erasureMechanism="Deleted when user turns 18",
        )
        assert cat.category == "children"
        assert cat.retentionPeriod == "Until age 18"


class TestROPADataCategory:
    def test_default_special_category(self):
        cat = ROPADataCategory(
            category="usage_data",
            description="Anonymous usage statistics",
            retentionPeriod="2 years",
            erasureMechanism="Automated purge",
            securityMeasures=["Pseudonymization"],
        )
        assert cat.specialCategory is False

    def test_security_measures_default(self):
        cat = ROPADataCategory(
            category="log_data",
            description="System logs",
            retentionPeriod="90 days",
            erasureMechanism="Rotated after 90 days",
            securityMeasures=[],
        )
        assert cat.securityMeasures == []


class TestGenerateROPAResponse:
    @pytest.mark.asyncio
    async def test_returns_ropa_report(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test-model",
            controllerName="Acme Corp",
            controllerAddress="123 Main St",
            controllerEmail="dpo@acme.com",
            processingPurposes=["Model training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="employees",
                    description="Employees",
                    retentionPeriod="3 years",
                    erasureMechanism="Delete after notice",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="performance_data",
                    description="Metrics",
                    retentionPeriod="5 years",
                    erasureMechanism="Archived then deleted",
                    securityMeasures=["Encryption"],
                )
            ],
            recipientCategories=["Cloud provider"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert isinstance(report, ROPAReport)
        assert report.modelId == "test-model"
        assert report.controllerName == "Acme Corp"

    @pytest.mark.asyncio
    async def test_ropa_id_is_generated(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test-model",
            controllerName="Acme Corp",
            controllerAddress="123 Main St",
            controllerEmail="dpo@acme.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="employees",
                    description="Employees",
                    retentionPeriod="3 years",
                    erasureMechanism="Auto-delete",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="perf",
                    description="Metrics",
                    retentionPeriod="5 years",
                    erasureMechanism="Archive",
                    securityMeasures=["Encryption"],
                )
            ],
            recipientCategories=["Provider"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert uuid.UUID(report.ropaId)

    @pytest.mark.asyncio
    async def test_all_fields_passed_through(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="model-123",
            controllerName="Big Corp",
            controllerRepresentative="Alice",
            dpoName="Bob",
            controllerAddress="456 Oak Ave",
            controllerEmail="dpo@bigcorp.com",
            jointControllers=["Joint Inc"],
            processingPurposes=["Training", "Inference"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Platform users",
                    retentionPeriod="3 years",
                    erasureMechanism="Account deletion",
                ),
            ],
            dataCategories=[
                ROPADataCategory(
                    category="email",
                    description="Email addresses",
                    retentionPeriod="3 years",
                    erasureMechanism="Deleted on account close",
                    securityMeasures=["Encryption"],
                ),
            ],
            recipientCategories=["AWS", "Datadog"],
            crossBorderTransfer=True,
            thirdCountries=["US", "Singapore"],
            transferSafeguards=["SCCs"],
            retentionScheduleDescription="Per category policy",
            securityMeasures=["TLS", "RBAC", "Encryption"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert report.controllerRepresentative == "Alice"
        assert report.dpoName == "Bob"
        assert report.jointControllers == ["Joint Inc"]
        assert report.crossBorderTransfer is True
        assert "US" in report.thirdCountries
        assert "SCCs" in report.transferSafeguards
        assert "TLS" in report.securityMeasures

    @pytest.mark.asyncio
    async def test_compliant_with_all_requirements(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test",
            controllerName="Compliant Corp",
            controllerAddress="Addr",
            controllerEmail="e@e.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Users",
                    retentionPeriod="3y",
                    erasureMechanism="Del",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="scores",
                    description="Prediction scores",
                    retentionPeriod="5 years",
                    erasureMechanism="Archived",
                    securityMeasures=["Encryption"],
                ),
            ],
            recipientCategories=["Cloud"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert report.compliant is True

    @pytest.mark.asyncio
    async def test_non_compliant_when_retention_missing(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test",
            controllerName="NonCompliant Corp",
            controllerAddress="Addr",
            controllerEmail="e@e.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Users",
                    retentionPeriod="3y",
                    erasureMechanism="Del",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="scores",
                    description="Prediction scores",
                    retentionPeriod="",
                    erasureMechanism="Archived",
                    securityMeasures=["Encryption"],
                ),
            ],
            recipientCategories=["Cloud"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert report.compliant is False

    @pytest.mark.asyncio
    async def test_non_compliant_when_no_controller_name(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test",
            controllerName="",
            controllerAddress="Addr",
            controllerEmail="e@e.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Users",
                    retentionPeriod="3y",
                    erasureMechanism="Del",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="scores",
                    description="Scores",
                    retentionPeriod="5y",
                    erasureMechanism="Archive",
                    securityMeasures=["Enc"],
                ),
            ],
            recipientCategories=["Cloud"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert report.compliant is False

    @pytest.mark.asyncio
    async def test_cross_border_without_safeguards_non_compliant(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test",
            controllerName="Corp",
            controllerAddress="Addr",
            controllerEmail="e@e.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Users",
                    retentionPeriod="3y",
                    erasureMechanism="Del",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="scores",
                    description="Scores",
                    retentionPeriod="5y",
                    erasureMechanism="Archive",
                    securityMeasures=["Enc"],
                ),
            ],
            recipientCategories=["Cloud"],
            crossBorderTransfer=True,
            thirdCountries=["US"],
            transferSafeguards=[],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert report.compliant is False

    @pytest.mark.asyncio
    async def test_regulatory_mappings_present(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test",
            controllerName="Corp",
            controllerAddress="Addr",
            controllerEmail="e@e.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Users",
                    retentionPeriod="3y",
                    erasureMechanism="Del",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="scores",
                    description="Scores",
                    retentionPeriod="5y",
                    erasureMechanism="Archive",
                    securityMeasures=["Enc"],
                ),
            ],
            recipientCategories=["Cloud"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert "GDPR Art. 30" in report.mappedArticles
        assert "ISO/IEC 42001:2023" in report.iso42001Clause

    @pytest.mark.asyncio
    async def test_retention_schedule_fallback(self, monkeypatch):
        monkeypatch.setattr("routers.ropa.record_audit_evidence", lambda **kw: None)
        req = GenerateROPARequest(
            modelId="test",
            controllerName="Corp",
            controllerAddress="Addr",
            controllerEmail="e@e.com",
            processingPurposes=["Training"],
            dataSubjectCategories=[
                ROPADataSubjectCategory(
                    category="users",
                    description="Users",
                    retentionPeriod="3y",
                    erasureMechanism="Del",
                )
            ],
            dataCategories=[
                ROPADataCategory(
                    category="scores",
                    description="Scores",
                    retentionPeriod="5y",
                    erasureMechanism="Archive",
                    securityMeasures=["Enc"],
                ),
            ],
            recipientCategories=["Cloud"],
        )
        report = await generate_ropa(req, request_obj=None)  # type: ignore
        assert "Retention periods are defined per data category" in report.retentionScheduleDescription
