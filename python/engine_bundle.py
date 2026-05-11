"""
ENGINE BUNDLE — Self-contained financial model for Pyodide (browser).

Section 1: All config classes, enums, constants, and dataclasses.
No external dependencies beyond Python stdlib.
No numpy, no pandas, no model.xxx imports.
"""

import math
import json
import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FundingScenario(Enum):
    BOOTSTRAP = "Bootstrap"
    PRE_SEED = "Pre-Seed"
    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"


class UsageVariant(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class UserProfile(Enum):
    SOLO = "Solo Indie"
    INDIE = "Indie Studio"
    NARRATIVE_DESIGNER = "Narrative Designer"
    AA = "AA Studio"
    AAA = "AAA Team"
    LIVE_SERVICE = "Live Service"


class StudioTier(Enum):
    INDIE = "Indie"
    AA = "AA"
    AAA = "AAA"
    LIVE_SERVICE = "Live Service"


class Role(Enum):
    # Wave 1 — Pre-Seed
    CEO = "CEO"
    CTO = "CTO"
    ENGINE_ENGINEER = "Engine Engineer"
    AI_ENGINEER = "AI Engineer"
    BUSINESS_DEV = "Business Developer"
    SUPPORT_ENGINEER = "Support Engineer"
    COMMUNITY_MANAGER = "Community Manager"
    SALES_1 = "Sales Rep 1"
    SALES_2 = "Sales Rep 2"
    # Wave 2 — Seed
    SALES_3 = "Sales Rep 3"
    SALES_4 = "Sales Rep 4"
    MARKETING_MANAGER = "Marketing Manager"
    SENIOR_ENGINEER = "Senior Engineer"
    DEVOPS = "DevOps Engineer"
    # Wave 3 — Series A
    VP_SALES = "VP Sales"
    VP_ENGINEERING = "VP Engineering"
    CFO = "CFO"
    SALES_5 = "Sales Rep 5"
    SALES_6 = "Sales Rep 6"
    SALES_7 = "Sales Rep 7"
    ENGINEER_3 = "Engineer 3"
    ENGINEER_4 = "Engineer 4"
    ENGINEER_5 = "Engineer 5"
    # Wave 4 — Series B
    SALES_8 = "Sales Rep 8"
    SALES_9 = "Sales Rep 9"
    SALES_10 = "Sales Rep 10"
    ENGINEER_6 = "Engineer 6"
    ENGINEER_7 = "Engineer 7"
    SUPPORT_2 = "Support Engineer 2"
    SUPPORT_3 = "Support Engineer 3"
    # Wave 5 — Customer Success (triggered by customer count)
    CUSTOMER_SUCCESS_1 = "Customer Success Manager"
    ACCOUNT_MANAGER_1 = "Account Manager"
    SOLUTIONS_ENGINEER = "Solutions Engineer"
    # Wave 6 — Scaling Operations
    HR_MANAGER = "HR Manager"
    OFFICE_MANAGER = "Office Manager"
    CUSTOMER_SUCCESS_2 = "Customer Success Manager 2"
    ACCOUNT_MANAGER_2 = "Account Manager 2"
    PRODUCT_MANAGER = "Product Manager"
    QA_ENGINEER = "QA Engineer"
    # Wave 7 — Leadership & Specialization
    COO = "COO"
    HEAD_OF_CS = "Head of Customer Success"
    DATA_ENGINEER = "Data Engineer"
    SECURITY_ENGINEER = "Security Engineer"
    TECHNICAL_WRITER = "Technical Writer"
    # Wave 8 — International Expansion
    REGIONAL_SALES_US = "Regional Sales (US)"
    REGIONAL_SALES_APAC = "Regional Sales (APAC)"
    LEGAL_COUNSEL = "Legal Counsel"
    # Wave 9 — Enterprise & Beyond-Gaming
    BD_BEYOND_GAMING = "BD Manager (Beyond Gaming)"
    SOLUTIONS_ARCHITECT = "Solutions Architect"
    COMPLIANCE_OFFICER = "Compliance Officer"
    PARTNER_MANAGER = "Partner Manager"


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimingConfig:
    model_start_year: int = 2026
    model_start_month: int = 4          # April 2026 (Q2)
    horizon_years: int = 10             # through Q1 2036
    monthly_detail_years: int = 2       # Y1-Y2 monthly
    # Y3-Y10 quarterly

    @property
    def total_months(self) -> int:
        return self.horizon_years * 12

    @property
    def monthly_months(self) -> int:
        return self.monthly_detail_years * 12


# ---------------------------------------------------------------------------
# Actuals (pre-model history)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Actuals:
    cash_at_start: float = 7_000        # EUR, 29 March 2026
    active_architect_users: int = 5
    raised_to_date: float = 50_000      # Aug 2025
    business_loan: float = 100_000      # EUR, business loan at model start
    business_loan_month: int = 0        # Month loan arrives (0 = model start)
    loan_term_months: int = 60          # 5-year term
    loan_interest_rate: float = 0.05    # 5% annual
    loan_grace_months: int = 6          # 6-month grace period before repayments start
    spent_personnel: float = 45_000     # CTO salary
    spent_legal_events: float = 5_000


# ---------------------------------------------------------------------------
# Token Economics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TokenEconomics:
    ai_model: str = "Claude Opus 4.5"
    input_rate_eur_per_m: float = 13.8      # EUR per 1M input tokens
    output_rate_eur_per_m: float = 69.0     # EUR per 1M output tokens
    system_prompt_overhead: float = 0.07    # 7%
    tokens_per_word: float = 1.25
    chunk_size_words: int = 28_000
    chunk_overlap: float = 0.20             # 20%
    markup_multiplier: float = 5.0          # 5x markup
    ai_cost_deflation_per_year: float = 0.20  # 20% drop per year
    payment_processing_rate: float = 0.017  # Stripe EU: 1.5% + ~EUR 0.20 avg per-txn fee
    fx_exchange_cost_rate: float = 0.02     # 2% currency exchange on international revenue


# ---------------------------------------------------------------------------
# Project Size Tiers (for token cost calculations)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectSizeTier:
    name: str
    lore_words: int
    chunks: int


PROJECT_SIZE_TIERS: Dict[UserProfile, ProjectSizeTier] = {
    UserProfile.SOLO: ProjectSizeTier("Solo", 23_000, 1),
    UserProfile.INDIE: ProjectSizeTier("Indie", 47_000, 2),
    UserProfile.NARRATIVE_DESIGNER: ProjectSizeTier("Indie", 47_000, 2),  # same as Indie
    UserProfile.AA: ProjectSizeTier("AA", 94_000, 4),
    UserProfile.AAA: ProjectSizeTier("AAA", 150_000, 7),
    UserProfile.LIVE_SERVICE: ProjectSizeTier("AA", 94_000, 4),  # similar to AA
}


# ---------------------------------------------------------------------------
# Feature Definitions (token usage per operation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureParams:
    name: str
    base_input_tokens: int
    base_output_tokens: int
    lore_passes: int
    cost_type: str              # "fixed", "per_chunk", "generation", "none"


FEATURES: List[FeatureParams] = [
    FeatureParams("Schema Generation",          7_500,  1_336,  0, "fixed"),
    FeatureParams("Entity Extraction",         35_000, 14_000,  0, "per_chunk"),
    FeatureParams("Export System",                  0,      0,  0, "none"),
    FeatureParams("Relationship Resolution",    8_000,  3_000,  1, "generation"),
    FeatureParams("Entity Generation",         32_800,  9_500,  1, "generation"),
    FeatureParams("Beat Generation",           20_900,  6_700,  1, "generation"),
    FeatureParams("Dialogue Generation",       11_100,  2_550,  1, "generation"),
    FeatureParams("Branch Node Generation",    16_950,  4_100,  1, "generation"),
    FeatureParams("Action Extraction",         50_500, 14_500,  1, "generation"),
    FeatureParams("Narrative Evaluation",      12_000,  2_000,  1, "generation"),
    FeatureParams("Natural Language Search",    1_500,    500,  1, "generation"),
    FeatureParams("World Bible Generation",    40_000, 15_000,  0, "fixed"),
    FeatureParams("Smart Code Comments",       10_500,  3_000,  0, "fixed"),
    FeatureParams("RAG Data Preparation",      20_500,  8_300,  0, "fixed"),
    FeatureParams("Fine-tuning Data Gen",      35_000, 14_500,  0, "fixed"),
]

FEATURE_NAMES: List[str] = [f.name for f in FEATURES]


# ---------------------------------------------------------------------------
# Feature Operations (ops/user/month) — Low / Medium / High
# Rows: features, Columns: user profiles
# ---------------------------------------------------------------------------

# fmt: off
FEATURE_OPS: Dict[UsageVariant, Dict[str, Dict[UserProfile, float]]] = {
    UsageVariant.LOW: {
        "Schema Generation":        {UserProfile.SOLO: 0.08, UserProfile.INDIE: 0.17, UserProfile.NARRATIVE_DESIGNER: 0.08, UserProfile.AA: 0.17, UserProfile.AAA: 0.17, UserProfile.LIVE_SERVICE: 0.08},
        "Entity Extraction":        {UserProfile.SOLO: 0.25, UserProfile.INDIE: 0.50, UserProfile.NARRATIVE_DESIGNER: 0.50, UserProfile.AA: 3.00, UserProfile.AAA: 8.00, UserProfile.LIVE_SERVICE: 1.00},
        "Export System":            {UserProfile.SOLO: 0.17, UserProfile.INDIE: 0.17, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.33, UserProfile.AAA: 0.50, UserProfile.LIVE_SERVICE: 0.17},
        "Relationship Resolution":  {UserProfile.SOLO: 0.08, UserProfile.INDIE: 0.50, UserProfile.NARRATIVE_DESIGNER: 0.50, UserProfile.AA: 1.50, UserProfile.AAA: 3.00, UserProfile.LIVE_SERVICE: 0.50},
        "Entity Generation":        {UserProfile.SOLO: 1.00, UserProfile.INDIE: 2.00, UserProfile.NARRATIVE_DESIGNER: 3.00, UserProfile.AA: 8.00, UserProfile.AAA: 15.0, UserProfile.LIVE_SERVICE: 4.00},
        "Beat Generation":          {UserProfile.SOLO: 0.50, UserProfile.INDIE: 1.00, UserProfile.NARRATIVE_DESIGNER: 4.00, UserProfile.AA: 12.0, UserProfile.AAA: 25.0, UserProfile.LIVE_SERVICE: 8.00},
        "Dialogue Generation":      {UserProfile.SOLO: 5.00, UserProfile.INDIE: 10.0, UserProfile.NARRATIVE_DESIGNER: 20.0, UserProfile.AA: 30.0, UserProfile.AAA: 40.0, UserProfile.LIVE_SERVICE: 25.0},
        "Branch Node Generation":   {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.50, UserProfile.NARRATIVE_DESIGNER: 2.00, UserProfile.AA: 4.00, UserProfile.AAA: 10.0, UserProfile.LIVE_SERVICE: 5.00},
        "Action Extraction":        {UserProfile.SOLO: 0.00, UserProfile.INDIE: 1.00, UserProfile.NARRATIVE_DESIGNER: 5.00, UserProfile.AA: 12.0, UserProfile.AAA: 25.0, UserProfile.LIVE_SERVICE: 10.0},
        "Narrative Evaluation":     {UserProfile.SOLO: 0.25, UserProfile.INDIE: 0.50, UserProfile.NARRATIVE_DESIGNER: 3.00, UserProfile.AA: 5.00, UserProfile.AAA: 12.0, UserProfile.LIVE_SERVICE: 4.00},
        "Natural Language Search":  {UserProfile.SOLO: 1.00, UserProfile.INDIE: 2.00, UserProfile.NARRATIVE_DESIGNER: 4.00, UserProfile.AA: 10.0, UserProfile.AAA: 15.0, UserProfile.LIVE_SERVICE: 12.0},
        "World Bible Generation":   {UserProfile.SOLO: 0.08, UserProfile.INDIE: 0.17, UserProfile.NARRATIVE_DESIGNER: 0.25, UserProfile.AA: 0.33, UserProfile.AAA: 0.50, UserProfile.LIVE_SERVICE: 0.08},
        "Smart Code Comments":      {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.17, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.33, UserProfile.AAA: 0.50, UserProfile.LIVE_SERVICE: 0.17},
        "RAG Data Preparation":     {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.08, UserProfile.AAA: 0.17, UserProfile.LIVE_SERVICE: 0.08},
        "Fine-tuning Data Gen":     {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.08, UserProfile.AAA: 0.08, UserProfile.LIVE_SERVICE: 0.08},
    },
    UsageVariant.MEDIUM: {
        "Schema Generation":        {UserProfile.SOLO: 0.33, UserProfile.INDIE: 0.33, UserProfile.NARRATIVE_DESIGNER: 0.17, UserProfile.AA: 0.33, UserProfile.AAA: 0.33, UserProfile.LIVE_SERVICE: 0.17},
        "Entity Extraction":        {UserProfile.SOLO: 0.50, UserProfile.INDIE: 2.00, UserProfile.NARRATIVE_DESIGNER: 1.50, UserProfile.AA: 8.00, UserProfile.AAA: 20.0, UserProfile.LIVE_SERVICE: 2.00},
        "Export System":            {UserProfile.SOLO: 0.33, UserProfile.INDIE: 0.50, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.50, UserProfile.AAA: 1.00, UserProfile.LIVE_SERVICE: 0.33},
        "Relationship Resolution":  {UserProfile.SOLO: 0.50, UserProfile.INDIE: 1.00, UserProfile.NARRATIVE_DESIGNER: 2.00, UserProfile.AA: 3.00, UserProfile.AAA: 6.00, UserProfile.LIVE_SERVICE: 1.50},
        "Entity Generation":        {UserProfile.SOLO: 2.00, UserProfile.INDIE: 5.00, UserProfile.NARRATIVE_DESIGNER: 8.00, UserProfile.AA: 15.0, UserProfile.AAA: 30.0, UserProfile.LIVE_SERVICE: 8.00},
        "Beat Generation":          {UserProfile.SOLO: 1.50, UserProfile.INDIE: 3.00, UserProfile.NARRATIVE_DESIGNER: 10.0, UserProfile.AA: 25.0, UserProfile.AAA: 50.0, UserProfile.LIVE_SERVICE: 18.0},
        "Dialogue Generation":      {UserProfile.SOLO: 15.0, UserProfile.INDIE: 30.0, UserProfile.NARRATIVE_DESIGNER: 60.0, UserProfile.AA: 60.0, UserProfile.AAA: 100., UserProfile.LIVE_SERVICE: 60.0},
        "Branch Node Generation":   {UserProfile.SOLO: 0.00, UserProfile.INDIE: 2.00, UserProfile.NARRATIVE_DESIGNER: 5.00, UserProfile.AA: 8.00, UserProfile.AAA: 20.0, UserProfile.LIVE_SERVICE: 10.0},
        "Action Extraction":        {UserProfile.SOLO: 0.00, UserProfile.INDIE: 3.00, UserProfile.NARRATIVE_DESIGNER: 15.0, UserProfile.AA: 30.0, UserProfile.AAA: 60.0, UserProfile.LIVE_SERVICE: 25.0},
        "Narrative Evaluation":     {UserProfile.SOLO: 0.50, UserProfile.INDIE: 2.00, UserProfile.NARRATIVE_DESIGNER: 8.00, UserProfile.AA: 12.0, UserProfile.AAA: 30.0, UserProfile.LIVE_SERVICE: 8.00},
        "Natural Language Search":  {UserProfile.SOLO: 3.00, UserProfile.INDIE: 8.00, UserProfile.NARRATIVE_DESIGNER: 10.0, UserProfile.AA: 25.0, UserProfile.AAA: 35.0, UserProfile.LIVE_SERVICE: 30.0},
        "World Bible Generation":   {UserProfile.SOLO: 0.17, UserProfile.INDIE: 0.33, UserProfile.NARRATIVE_DESIGNER: 0.50, UserProfile.AA: 0.50, UserProfile.AAA: 1.00, UserProfile.LIVE_SERVICE: 0.25},
        "Smart Code Comments":      {UserProfile.SOLO: 0.17, UserProfile.INDIE: 0.33, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.50, UserProfile.AAA: 1.00, UserProfile.LIVE_SERVICE: 0.33},
        "RAG Data Preparation":     {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.17, UserProfile.AAA: 0.33, UserProfile.LIVE_SERVICE: 0.17},
        "Fine-tuning Data Gen":     {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.17, UserProfile.AAA: 0.25, UserProfile.LIVE_SERVICE: 0.08},
    },
    UsageVariant.HIGH: {
        "Schema Generation":        {UserProfile.SOLO: 0.50, UserProfile.INDIE: 0.50, UserProfile.NARRATIVE_DESIGNER: 0.33, UserProfile.AA: 0.50, UserProfile.AAA: 0.67, UserProfile.LIVE_SERVICE: 0.33},
        "Entity Extraction":        {UserProfile.SOLO: 1.00, UserProfile.INDIE: 4.00, UserProfile.NARRATIVE_DESIGNER: 3.00, UserProfile.AA: 15.0, UserProfile.AAA: 40.0, UserProfile.LIVE_SERVICE: 4.00},
        "Export System":            {UserProfile.SOLO: 0.50, UserProfile.INDIE: 1.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 1.00, UserProfile.AAA: 2.00, UserProfile.LIVE_SERVICE: 0.67},
        "Relationship Resolution":  {UserProfile.SOLO: 1.00, UserProfile.INDIE: 2.00, UserProfile.NARRATIVE_DESIGNER: 4.00, UserProfile.AA: 6.00, UserProfile.AAA: 12.0, UserProfile.LIVE_SERVICE: 3.00},
        "Entity Generation":        {UserProfile.SOLO: 4.00, UserProfile.INDIE: 10.0, UserProfile.NARRATIVE_DESIGNER: 15.0, UserProfile.AA: 30.0, UserProfile.AAA: 60.0, UserProfile.LIVE_SERVICE: 15.0},
        "Beat Generation":          {UserProfile.SOLO: 3.00, UserProfile.INDIE: 6.00, UserProfile.NARRATIVE_DESIGNER: 20.0, UserProfile.AA: 50.0, UserProfile.AAA: 100., UserProfile.LIVE_SERVICE: 35.0},
        "Dialogue Generation":      {UserProfile.SOLO: 30.0, UserProfile.INDIE: 60.0, UserProfile.NARRATIVE_DESIGNER: 120., UserProfile.AA: 120., UserProfile.AAA: 200., UserProfile.LIVE_SERVICE: 120.},
        "Branch Node Generation":   {UserProfile.SOLO: 0.00, UserProfile.INDIE: 4.00, UserProfile.NARRATIVE_DESIGNER: 10.0, UserProfile.AA: 15.0, UserProfile.AAA: 40.0, UserProfile.LIVE_SERVICE: 20.0},
        "Action Extraction":        {UserProfile.SOLO: 0.00, UserProfile.INDIE: 6.00, UserProfile.NARRATIVE_DESIGNER: 30.0, UserProfile.AA: 60.0, UserProfile.AAA: 120., UserProfile.LIVE_SERVICE: 50.0},
        "Narrative Evaluation":     {UserProfile.SOLO: 1.00, UserProfile.INDIE: 4.00, UserProfile.NARRATIVE_DESIGNER: 15.0, UserProfile.AA: 25.0, UserProfile.AAA: 60.0, UserProfile.LIVE_SERVICE: 15.0},
        "Natural Language Search":  {UserProfile.SOLO: 6.00, UserProfile.INDIE: 15.0, UserProfile.NARRATIVE_DESIGNER: 20.0, UserProfile.AA: 50.0, UserProfile.AAA: 70.0, UserProfile.LIVE_SERVICE: 60.0},
        "World Bible Generation":   {UserProfile.SOLO: 0.33, UserProfile.INDIE: 0.67, UserProfile.NARRATIVE_DESIGNER: 1.00, UserProfile.AA: 1.00, UserProfile.AAA: 2.00, UserProfile.LIVE_SERVICE: 0.50},
        "Smart Code Comments":      {UserProfile.SOLO: 0.33, UserProfile.INDIE: 0.67, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 1.00, UserProfile.AAA: 2.00, UserProfile.LIVE_SERVICE: 0.67},
        "RAG Data Preparation":     {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.33, UserProfile.AAA: 0.67, UserProfile.LIVE_SERVICE: 0.33},
        "Fine-tuning Data Gen":     {UserProfile.SOLO: 0.00, UserProfile.INDIE: 0.00, UserProfile.NARRATIVE_DESIGNER: 0.00, UserProfile.AA: 0.33, UserProfile.AAA: 0.50, UserProfile.LIVE_SERVICE: 0.17},
    },
}
# fmt: on


# ---------------------------------------------------------------------------
# Personnel
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoleConfig:
    role: Role
    monthly_gross: float            # EUR gross salary
    is_rd: bool                     # qualifies for WBSO?
    generates_leads: bool           # drives pipeline?
    lead_type: str = ""             # "b2b_warm", "b2b_outreach", "b2c_social", "b2b_sales"
    leads_per_month: float = 0.0
    lead_conversion: float = 0.0


ROLE_CONFIGS: List[RoleConfig] = [
    # Wave 1 — Pre-Seed
    RoleConfig(Role.CEO,               5_000, is_rd=False, generates_leads=True,  lead_type="b2b_warm",     leads_per_month=4,  lead_conversion=0.25),
    RoleConfig(Role.CTO,               7_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.ENGINE_ENGINEER,   5_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.AI_ENGINEER,       5_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.BUSINESS_DEV,      4_000, is_rd=False, generates_leads=True,  lead_type="b2b_outreach", leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SUPPORT_ENGINEER,  4_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.COMMUNITY_MANAGER, 4_000, is_rd=False, generates_leads=True,  lead_type="b2c_social",   leads_per_month=20, lead_conversion=0.10),
    RoleConfig(Role.SALES_1,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SALES_2,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    # Wave 2 — Seed
    RoleConfig(Role.SALES_3,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SALES_4,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.MARKETING_MANAGER, 5_000, is_rd=False, generates_leads=True,  lead_type="b2c_social",   leads_per_month=15, lead_conversion=0.10),
    RoleConfig(Role.SENIOR_ENGINEER,   7_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.DEVOPS,            5_000, is_rd=True,  generates_leads=False),
    # Wave 3 — Series A
    RoleConfig(Role.VP_SALES,          8_000, is_rd=False, generates_leads=True,  lead_type="b2b_warm",     leads_per_month=6,  lead_conversion=0.20),
    RoleConfig(Role.VP_ENGINEERING,    8_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.CFO,               7_000, is_rd=False, generates_leads=False),
    RoleConfig(Role.SALES_5,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SALES_6,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SALES_7,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.ENGINEER_3,        5_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.ENGINEER_4,        5_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.ENGINEER_5,        5_000, is_rd=True,  generates_leads=False),
    # Wave 4 — Series B
    RoleConfig(Role.SALES_8,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SALES_9,           4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.SALES_10,          4_000, is_rd=False, generates_leads=True,  lead_type="b2b_sales",    leads_per_month=8,  lead_conversion=0.15),
    RoleConfig(Role.ENGINEER_6,        5_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.ENGINEER_7,        5_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.SUPPORT_2,         4_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.SUPPORT_3,         4_000, is_rd=True,  generates_leads=False),
    # Wave 5 — Customer Success
    RoleConfig(Role.CUSTOMER_SUCCESS_1, 4_500, is_rd=False, generates_leads=False),
    RoleConfig(Role.ACCOUNT_MANAGER_1,  5_000, is_rd=False, generates_leads=True, lead_type="b2b_warm", leads_per_month=3, lead_conversion=0.20),
    RoleConfig(Role.SOLUTIONS_ENGINEER, 6_000, is_rd=True,  generates_leads=False),
    # Wave 6 — Scaling Operations
    RoleConfig(Role.HR_MANAGER,         5_000, is_rd=False, generates_leads=False),
    RoleConfig(Role.OFFICE_MANAGER,     3_500, is_rd=False, generates_leads=False),
    RoleConfig(Role.CUSTOMER_SUCCESS_2, 4_500, is_rd=False, generates_leads=False),
    RoleConfig(Role.ACCOUNT_MANAGER_2,  5_000, is_rd=False, generates_leads=True, lead_type="b2b_warm", leads_per_month=3, lead_conversion=0.20),
    RoleConfig(Role.PRODUCT_MANAGER,    6_000, is_rd=False, generates_leads=False),
    RoleConfig(Role.QA_ENGINEER,        4_500, is_rd=True,  generates_leads=False),
    # Wave 7 — Leadership & Specialization
    RoleConfig(Role.COO,                8_000, is_rd=False, generates_leads=False),
    RoleConfig(Role.HEAD_OF_CS,         7_000, is_rd=False, generates_leads=False),
    RoleConfig(Role.DATA_ENGINEER,      5_500, is_rd=True,  generates_leads=False),
    RoleConfig(Role.SECURITY_ENGINEER,  6_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.TECHNICAL_WRITER,   4_000, is_rd=False, generates_leads=False),
    # Wave 8 — International Expansion
    RoleConfig(Role.REGIONAL_SALES_US,  5_000, is_rd=False, generates_leads=True, lead_type="b2b_sales", leads_per_month=8, lead_conversion=0.15),
    RoleConfig(Role.REGIONAL_SALES_APAC,4_000, is_rd=False, generates_leads=True, lead_type="b2b_sales", leads_per_month=8, lead_conversion=0.15),
    RoleConfig(Role.LEGAL_COUNSEL,      7_000, is_rd=False, generates_leads=False),
    # Wave 9 — Enterprise & Beyond-Gaming
    RoleConfig(Role.BD_BEYOND_GAMING,   6_000, is_rd=False, generates_leads=True, lead_type="b2b_outreach", leads_per_month=6, lead_conversion=0.15),
    RoleConfig(Role.SOLUTIONS_ARCHITECT,7_000, is_rd=True,  generates_leads=False),
    RoleConfig(Role.COMPLIANCE_OFFICER, 5_500, is_rd=False, generates_leads=False),
    RoleConfig(Role.PARTNER_MANAGER,    5_000, is_rd=False, generates_leads=False),
]

ROLE_CONFIG_MAP: Dict[Role, RoleConfig] = {rc.role: rc for rc in ROLE_CONFIGS}


@dataclass(frozen=True)
class EmployerCosts:
    social_security_rate: float = 0.20      # ~20%
    vakantiegeld_rate: float = 0.08         # 8% holiday allowance
    pension_rate: float = 0.10              # ~10%

    @property
    def total_rate(self) -> float:
        return self.social_security_rate + self.vakantiegeld_rate + self.pension_rate  # ~38%


@dataclass(frozen=True)
class WBSOConfig:
    rd_qualifying_share: float = 0.60       # 60% of R&D work qualifies
    benefit_rate: float = 0.50              # 50% benefit on qualifying portion

    @property
    def effective_reduction(self) -> float:
        return self.rd_qualifying_share * self.benefit_rate  # ~30%


# Salary increases step down after initial catch-up period
SALARY_INCREASE_SCHEDULE: List[Tuple[int, float]] = [
    (0, 0.10),    # Y1-Y3: 10% (catch-up from below-market startup salaries)
    (36, 0.05),   # Y4+: 5% (market rate + inflation)
]
# Keep the old constant for backward compatibility
SALARY_ANNUAL_INCREASE: float = 0.10

# FTE schedule overrides — roles not listed here are 1.0 FTE when active.
# Each entry: Role -> list of (from_model_month, fte_fraction).
# Model starts April 2026, so month 9 = January 2027.
FTE_SCHEDULE: Dict[Role, List[Tuple[int, float]]] = {
    Role.AI_ENGINEER: [
        (0, 0.4),    # 16 hrs/week (40%) until Jan 2027
        (9, 0.6),    # 3 days/week (60%) for 2027
        (21, 1.0),   # Full-time from Jan 2028
    ],
    Role.COMMUNITY_MANAGER: [
        (0, 0.6),    # 3 days/week (60%) for 2027
        (21, 1.0),   # Full-time from Jan 2028
    ],
}

# Salary overrides — roles not listed use the base monthly_gross from RoleConfig.
# Each entry: Role -> list of (from_model_month, monthly_gross_eur).
# Overrides the RoleConfig.monthly_gross for that period (before annual raises).
# NOTE: When an override exists, it takes precedence over the RoleConfig.monthly_gross
# for actual payroll. The RoleConfig base (e.g. BD 4K) represents the eventual full rate;
# the override controls what is actually paid during the ramp period.
SALARY_OVERRIDE: Dict[Role, List[Tuple[int, float]]] = {
    Role.BUSINESS_DEV: [
        (0, 1_500),    # 2026: Kiomi starts at EUR 1.5K/mo
        (9, 2_000),    # 2027: ramp to EUR 2K/mo
        (21, 3_000),   # 2028+: ramp to EUR 3K/mo (RoleConfig base: 4K is eventual full rate)
    ],
}


# ---------------------------------------------------------------------------
# Hiring Sequences (gated by funding scenario)
# Tuple of (Role, month offset from funding event)
# Month 0 = funding arrives (or model start for bootstrap)
# ---------------------------------------------------------------------------

# Bootstrap hiring config: revenue threshold before each hire triggers
BOOTSTRAP_HIRE_REVENUE_MULTIPLIER: float = 1.5  # monthly rev > payroll * 1.5
BOOTSTRAP_HIRE_CONSECUTIVE_MONTHS: int = 2       # must sustain for 2 months
BOOTSTRAP_HIRE_ORDER: List[Role] = [
    Role.CEO, Role.CTO,
    Role.ENGINE_ENGINEER, Role.AI_ENGINEER, Role.BUSINESS_DEV,
    Role.SUPPORT_ENGINEER, Role.COMMUNITY_MANAGER,
    Role.SALES_1, Role.SALES_2,
]

HIRING_SEQUENCES: Dict[FundingScenario, List[Tuple[Role, int]]] = {
    FundingScenario.BOOTSTRAP: [
        # Dynamic — handled in personnel.py using BOOTSTRAP_HIRE_ORDER
        # Listed here as empty; personnel.py checks BOOTSTRAP_HIRE_ORDER
    ],
    FundingScenario.PRE_SEED: [
        # Wave 1
        (Role.CEO,               0),    # immediately on funding
        (Role.CTO,               0),
        (Role.ENGINE_ENGINEER,   2),
        (Role.AI_ENGINEER,       2),    # Jesse — founding team
        (Role.BUSINESS_DEV,      2),
        (Role.SUPPORT_ENGINEER,  6),
        (Role.COMMUNITY_MANAGER, 6),
        (Role.SALES_1,           9),
        (Role.SALES_2,          12),
        # Wave 5 — Customer Success
        (Role.CUSTOMER_SUCCESS_1, 15),
        (Role.ACCOUNT_MANAGER_1,  24),
        (Role.SOLUTIONS_ENGINEER, 30),
    ],
    FundingScenario.SEED: [
        # Wave 1
        (Role.CEO,               0),
        (Role.CTO,               0),
        (Role.ENGINE_ENGINEER,   1),
        (Role.AI_ENGINEER,       1),
        (Role.BUSINESS_DEV,      1),
        (Role.SUPPORT_ENGINEER,  3),
        (Role.COMMUNITY_MANAGER, 3),
        (Role.SALES_1,           4),
        (Role.SALES_2,           6),
        # Wave 2 — relative to Seed funding (month 18)
        (Role.SALES_3,           7),
        (Role.SALES_4,           9),
        (Role.MARKETING_MANAGER, 8),
        (Role.SENIOR_ENGINEER,   7),
        (Role.DEVOPS,           10),
        # Wave 5
        (Role.CUSTOMER_SUCCESS_1, 12),
        (Role.ACCOUNT_MANAGER_1,  18),
        (Role.SOLUTIONS_ENGINEER, 24),
        # Wave 6
        (Role.HR_MANAGER,         30),
        (Role.PRODUCT_MANAGER,    36),
        (Role.QA_ENGINEER,        36),
        (Role.CUSTOMER_SUCCESS_2, 42),
    ],
    FundingScenario.SERIES_A: [
        # Wave 1
        (Role.CEO,               0),
        (Role.CTO,               0),
        (Role.ENGINE_ENGINEER,   1),
        (Role.AI_ENGINEER,       1),
        (Role.BUSINESS_DEV,      1),
        (Role.SUPPORT_ENGINEER,  2),
        (Role.COMMUNITY_MANAGER, 2),
        (Role.SALES_1,           3),
        (Role.SALES_2,           4),
        # Wave 2
        (Role.SALES_3,           5),
        (Role.SALES_4,           7),
        (Role.MARKETING_MANAGER, 6),
        (Role.SENIOR_ENGINEER,   5),
        (Role.DEVOPS,            8),
        # Wave 3 — relative to Series A funding (month 30)
        (Role.VP_SALES,          6),
        (Role.VP_ENGINEERING,    6),
        (Role.CFO,               9),
        (Role.SALES_5,           8),
        (Role.SALES_6,          10),
        (Role.SALES_7,          12),
        (Role.ENGINEER_3,        7),
        (Role.ENGINEER_4,        9),
        (Role.ENGINEER_5,       12),
        # Wave 5
        (Role.CUSTOMER_SUCCESS_1, 8),
        (Role.ACCOUNT_MANAGER_1,  14),
        (Role.SOLUTIONS_ENGINEER, 18),
        # Wave 6
        (Role.HR_MANAGER,         20),
        (Role.OFFICE_MANAGER,     24),
        (Role.PRODUCT_MANAGER,    24),
        (Role.QA_ENGINEER,        26),
        (Role.CUSTOMER_SUCCESS_2, 30),
        (Role.ACCOUNT_MANAGER_2,  36),
        # Wave 7
        (Role.COO,                36),
        (Role.HEAD_OF_CS,         42),
        (Role.DATA_ENGINEER,      38),
        (Role.SECURITY_ENGINEER,  42),
        (Role.TECHNICAL_WRITER,   40),
        # Wave 8
        (Role.REGIONAL_SALES_US,  48),
        (Role.REGIONAL_SALES_APAC, 54),
        (Role.LEGAL_COUNSEL,      48),
    ],
    FundingScenario.SERIES_B: [
        # Wave 1
        (Role.CEO,               0),
        (Role.CTO,               0),
        (Role.ENGINE_ENGINEER,   1),
        (Role.AI_ENGINEER,       1),
        (Role.BUSINESS_DEV,      1),
        (Role.SUPPORT_ENGINEER,  2),
        (Role.COMMUNITY_MANAGER, 2),
        (Role.SALES_1,           3),
        (Role.SALES_2,           4),
        # Wave 2
        (Role.SALES_3,           5),
        (Role.SALES_4,           7),
        (Role.MARKETING_MANAGER, 6),
        (Role.SENIOR_ENGINEER,   5),
        (Role.DEVOPS,            8),
        # Wave 3
        (Role.VP_SALES,          6),
        (Role.VP_ENGINEERING,    6),
        (Role.CFO,               9),
        (Role.SALES_5,           8),
        (Role.SALES_6,          10),
        (Role.SALES_7,          12),
        (Role.ENGINEER_3,        7),
        (Role.ENGINEER_4,        9),
        (Role.ENGINEER_5,       12),
        # Wave 4 — relative to Series B funding (month 42)
        (Role.SALES_8,           2),
        (Role.SALES_9,           4),
        (Role.SALES_10,          6),
        (Role.ENGINEER_6,        3),
        (Role.ENGINEER_7,        5),
        (Role.SUPPORT_2,         3),
        (Role.SUPPORT_3,         6),
        # Wave 5
        (Role.CUSTOMER_SUCCESS_1, 8),
        (Role.ACCOUNT_MANAGER_1,  14),
        (Role.SOLUTIONS_ENGINEER, 18),
        # Wave 6
        (Role.HR_MANAGER,         20),
        (Role.OFFICE_MANAGER,     24),
        (Role.PRODUCT_MANAGER,    24),
        (Role.QA_ENGINEER,        26),
        (Role.CUSTOMER_SUCCESS_2, 30),
        (Role.ACCOUNT_MANAGER_2,  36),
        # Wave 7
        (Role.COO,                36),
        (Role.HEAD_OF_CS,         42),
        (Role.DATA_ENGINEER,      38),
        (Role.SECURITY_ENGINEER,  42),
        (Role.TECHNICAL_WRITER,   40),
        # Wave 8
        (Role.REGIONAL_SALES_US,  48),
        (Role.REGIONAL_SALES_APAC, 54),
        (Role.LEGAL_COUNSEL,      48),
        # Wave 9 — Beyond Gaming
        (Role.BD_BEYOND_GAMING,    48),
        (Role.SOLUTIONS_ARCHITECT, 54),
        (Role.COMPLIANCE_OFFICER,  60),
        (Role.PARTNER_MANAGER,     60),
    ],
}


# ---------------------------------------------------------------------------
# Funding Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FundingEvent:
    amount: float
    month: int              # month offset from model start (0 = Apr 2026)
    pre_money_valuation: float
    dilution_pct: float     # % of company sold


FUNDING_EVENTS: Dict[FundingScenario, List] = {
    FundingScenario.BOOTSTRAP: [],
    FundingScenario.PRE_SEED: [
        FundingEvent(550_000, 3, 4_000_000, 0.12),       # Q3 2026 (~Jul), ~12% dilution
    ],
    FundingScenario.SEED: [
        FundingEvent(550_000, 3, 4_000_000, 0.12),        # Pre-Seed Q3 2026
        FundingEvent(2_500_000, 18, 12_000_000, 0.17),    # Seed Q4 2027
    ],
    FundingScenario.SERIES_A: [
        FundingEvent(550_000, 3, 4_000_000, 0.12),
        FundingEvent(2_500_000, 18, 12_000_000, 0.17),
        FundingEvent(10_000_000, 30, 40_000_000, 0.20),   # Series A ~Q4 2028
    ],
    FundingScenario.SERIES_B: [
        FundingEvent(550_000, 3, 4_000_000, 0.12),
        FundingEvent(2_500_000, 18, 12_000_000, 0.17),
        FundingEvent(10_000_000, 30, 40_000_000, 0.20),
        FundingEvent(30_000_000, 42, 120_000_000, 0.20),  # Series B ~Q4 2029
    ],
}


# ---------------------------------------------------------------------------
# Sales Pipeline
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineConfig:
    b2b_tier_split: Dict[StudioTier, float] = field(default_factory=lambda: {
        StudioTier.INDIE: 0.85,
        StudioTier.AA: 0.12,
        StudioTier.AAA: 0.03,
    })
    # Conversion improvement over time (annual)
    opp_rate_start: float = 0.20
    opp_rate_end: float = 0.50
    opp_rate_years_to_mature: int = 4
    close_rate_start: float = 0.075
    close_rate_end: float = 0.25
    close_rate_years_to_mature: int = 4
    # B2C / organic
    organic_signups_start: float = 30.0     # Base rate; overridden by ScenarioMultipliers per variant
    organic_growth_rate: float = 0.07       # Base rate; overridden by ScenarioMultipliers per variant
    organic_conversion_to_paid: float = 0.30  # Base rate; overridden by ScenarioMultipliers per variant
    # Events
    event_close_rate: float = 0.10              # B2B close rate for event-sourced leads (conservative)
    paid_users_per_event: int = 12
    # NOTE: max_active_customers moved to ScenarioMultipliers (TAM-derived per variant)
    # Director cross-sell
    director_to_architect_crosssell: float = 0.30  # B2B SaaS benchmark (OpenView: 15-30%)
    # Sales cycle length (months from close to active/paying)
    sales_cycle_months: Dict[UserProfile, int] = field(default_factory=lambda: {
        UserProfile.SOLO: 0,                # PLG, instant
        UserProfile.INDIE: 2,
        UserProfile.NARRATIVE_DESIGNER: 2,  # same as Indie
        UserProfile.AA: 4,
        UserProfile.AAA: 8,
        UserProfile.LIVE_SERVICE: 4,        # same as AA
    })


# ---------------------------------------------------------------------------
# Scenario Variant Multipliers
# Low/Medium/High affects the entire business execution, not just token usage.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioMultipliers:
    """Multipliers applied per usage variant to scale business performance."""
    lead_multiplier: float              # Multiplied into all lead generation rates
    conversion_multiplier: float        # Multiplied into all close/conversion rates
    organic_signups_start: float        # Override for organic signups base (per month)
    organic_growth_rate: float          # Override for organic MoM growth
    organic_conversion_to_paid: float   # Override for organic free-to-paid rate
    churn_multiplier: float             # Multiplied into churn rates (lower = less churn)
    director_adoption_multiplier: float # Multiplied into Director adoption rate
    beyond_gaming_multiplier: float     # Multiplied into beyond-gaming customer count
    # --- TAM-derived customer caps (replace arbitrary market_cap_multiplier) ---
    max_active_customers: Dict[UserProfile, int]  # Market-research-backed caps per variant
    # --- Beyond-gaming market sizing per variant ---
    beyond_gaming_market_2030: float    # Total world-model market size in EUR
    beyond_gaming_market_2035: float
    beyond_gaming_penetration_2035: float  # Our market share by 2035 (no narrative share filter -- penetration is direct)
    beyond_gaming_first_revenue_month: int  # Month when first beyond-gaming revenue starts
    beyond_gaming_ramp_midpoint: int    # Months after first revenue to reach 50% of target penetration
    beyond_gaming_ramp_steepness: float # Logistic S-curve steepness (higher = sharper ramp)
    # --- Director gaming TAM per variant ---
    director_tam_2030: float            # EUR
    director_tam_2035: float            # EUR
    event_lead_multiplier: float        # Multiplied into event lead generation
    ai_cost_deflation: float            # Override for AI cost deflation per year
    support_capacity: int               # Users per support engineer
    cs_capacity: int                    # B2B accounts per CS manager
    account_mgr_capacity: int           # AA+AAA accounts per account manager
    engineer_capacity: int              # Users per engineer (infrastructure scale)


SCENARIO_MULTIPLIERS: Dict[UsageVariant, ScenarioMultipliers] = {
    UsageVariant.LOW: ScenarioMultipliers(
        lead_multiplier=1.0,
        conversion_multiplier=1.0,
        organic_signups_start=30.0,
        organic_growth_rate=0.05,
        organic_conversion_to_paid=0.20,
        churn_multiplier=1.0,
        director_adoption_multiplier=0.8,
        beyond_gaming_multiplier=0.7,
        max_active_customers={
            UserProfile.SOLO: 105_000,
            UserProfile.INDIE: 6_000,
            UserProfile.NARRATIVE_DESIGNER: 1_000,
            UserProfile.AA: 75,
            UserProfile.AAA: 12,
            UserProfile.LIVE_SERVICE: 50,
        },
        beyond_gaming_market_2030=150e9,       # EUR 150B -- market still nascent
        beyond_gaming_market_2035=400e9,       # EUR 400B
        beyond_gaming_penetration_2035=0.05,   # 5%
        beyond_gaming_first_revenue_month=36,  # Y4 (2029) -- platforms barely exist in Low
        beyond_gaming_ramp_midpoint=60,        # Slow ramp -- 50% of target ~5 years after start
        beyond_gaming_ramp_steepness=0.04,     # Gradual S-curve
        director_tam_2030=0.2e9,               # EUR 0.2B
        director_tam_2035=1.2e9,               # EUR 1.2B
        event_lead_multiplier=1.0,
        ai_cost_deflation=0.15,
        support_capacity=1000,
        cs_capacity=30,
        account_mgr_capacity=10,
        engineer_capacity=5000,
    ),
    UsageVariant.MEDIUM: ScenarioMultipliers(
        lead_multiplier=1.5,
        conversion_multiplier=1.25,
        organic_signups_start=45.0,
        organic_growth_rate=0.07,
        organic_conversion_to_paid=0.30,
        churn_multiplier=0.8,
        director_adoption_multiplier=1.0,
        beyond_gaming_multiplier=1.0,
        max_active_customers={
            UserProfile.SOLO: 375_000,
            UserProfile.INDIE: 21_000,
            UserProfile.NARRATIVE_DESIGNER: 3_500,
            UserProfile.AA: 270,
            UserProfile.AAA: 43,
            UserProfile.LIVE_SERVICE: 180,
        },
        beyond_gaming_market_2030=200e9,       # EUR 200B
        beyond_gaming_market_2035=600e9,       # EUR 600B
        beyond_gaming_penetration_2035=0.20,   # 20%
        beyond_gaming_first_revenue_month=24,  # Y3 (2028) -- some platforms shipping
        beyond_gaming_ramp_midpoint=48,        # Moderate ramp
        beyond_gaming_ramp_steepness=0.06,     # Standard S-curve
        director_tam_2030=0.8e9,               # EUR 0.8B
        director_tam_2035=4.8e9,               # EUR 4.8B
        event_lead_multiplier=1.25,
        ai_cost_deflation=0.20,
        support_capacity=1500,
        cs_capacity=40,
        account_mgr_capacity=12,
        engineer_capacity=7500,
    ),
    UsageVariant.HIGH: ScenarioMultipliers(
        lead_multiplier=2.0,
        conversion_multiplier=1.5,
        organic_signups_start=60.0,
        organic_growth_rate=0.10,
        organic_conversion_to_paid=0.40,
        churn_multiplier=0.6,
        director_adoption_multiplier=1.25,
        beyond_gaming_multiplier=1.5,
        max_active_customers={
            UserProfile.SOLO: 830_000,
            UserProfile.INDIE: 47_000,
            UserProfile.NARRATIVE_DESIGNER: 7_900,
            UserProfile.AA: 590,
            UserProfile.AAA: 95,
            UserProfile.LIVE_SERVICE: 395,
        },
        beyond_gaming_market_2030=250e9,       # EUR 250B
        beyond_gaming_market_2035=800e9,       # EUR 800B
        beyond_gaming_penetration_2035=0.40,   # 40%
        beyond_gaming_first_revenue_month=15,  # Mid-Y2 (2027) -- early adopters integrating
        beyond_gaming_ramp_midpoint=36,        # Fast ramp -- strong product-market fit
        beyond_gaming_ramp_steepness=0.08,     # Sharp S-curve
        director_tam_2030=3.0e9,               # EUR 3.0B
        director_tam_2035=15.8e9,              # EUR 15.8B
        event_lead_multiplier=1.5,
        ai_cost_deflation=0.30,
        support_capacity=2000,
        cs_capacity=50,
        account_mgr_capacity=15,
        engineer_capacity=10000,
    ),
}


# ---------------------------------------------------------------------------
# Churn
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChurnConfig:
    monthly_rates: Dict[UserProfile, float] = field(default_factory=lambda: {
        UserProfile.SOLO: 0.05,             # 5%/mo ~ 46% annual (mid-range PLG)
        UserProfile.INDIE: 0.045,
        UserProfile.NARRATIVE_DESIGNER: 0.045,  # same as Indie
        UserProfile.AA: 0.02,
        UserProfile.AAA: 0.015,
        UserProfile.LIVE_SERVICE: 0.02,         # same as AA
    })
    annual_improvement: float = 0.10            # 10% improvement per year


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DirectorConfig:
    royalty_rate: float = 0.01              # 1%
    revenue_threshold: float = 100_000      # per game

    # Average game revenue per studio tier
    # These are per-tier averages, NOT a blended distribution.
    # Sources: VG Insights Steam revenue data, Newzoo, GDC State of Industry 2024
    avg_game_revenue: Dict[StudioTier, float] = field(default_factory=lambda: {
        StudioTier.INDIE: 500_000,          # EUR 500K -- median commercial indie
        StudioTier.AA: 10_000_000,          # EUR 10M -- mid-range AA title
        StudioTier.AAA: 75_000_000,         # EUR 75M -- average AAA (range: 20M-500M+)
        StudioTier.LIVE_SERVICE: 15_000_000, # EUR 15M/yr -- ongoing GaaS revenue
    })

    # Dev cycles (months from sign to ship)
    dev_cycle_months: Dict[StudioTier, int] = field(default_factory=lambda: {
        StudioTier.INDIE: 24,
        StudioTier.AA: 42,
        StudioTier.AAA: 66,
        StudioTier.LIVE_SERVICE: 3,     # already in production
    })

    # Royalty per game by tier (derived)
    @property
    def royalty_per_game(self) -> Dict[StudioTier, float]:
        return {
            tier: self.royalty_rate * max(0, rev - self.revenue_threshold)
            for tier, rev in self.avg_game_revenue.items()
        }


# ---------------------------------------------------------------------------
# Director Add-Ons
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AddOn:
    name: str
    price: float
    cogs_pct: float
    recurring: bool = False     # True = annual, False = one-time


DIRECTOR_ADDONS: List[AddOn] = [
    AddOn("Fine-tuning on studio lore",          30_000, 0.12),
    AddOn("Specialised agent packs",            120_000, 0.19),
    AddOn("Custom pipelines / engine port",      65_000, 0.32),
    AddOn("On-prem deployment & audit",         110_000, 0.22),
    AddOn("Game-setting starter packs",           3_000, 0.00),
    AddOn("Premium 24/7 SLA",                    50_000, 1.00, recurring=True),
]

# Attach rates by studio tier (probability of buying any add-on)
ADDON_ATTACH_RATES: Dict[StudioTier, float] = {
    StudioTier.INDIE: 0.20,
    StudioTier.AA: 0.60,
    StudioTier.AAA: 0.60,
    StudioTier.LIVE_SERVICE: 0.40,
}

# Average add-on spend by tier (one-time, across all add-ons)
ADDON_AVG_SPEND: Dict[StudioTier, float] = {
    StudioTier.INDIE: 6_000,
    StudioTier.AA: 107_000,
    StudioTier.AAA: 233_000,
    StudioTier.LIVE_SERVICE: 50_000,
}

# Royalty per game by tier: 1% of (avg game revenue - 100K threshold)
# Indie: 1% x (500K - 100K) = EUR 4,000
# AA: 1% x (10M - 100K) = EUR 99,000
# AAA: 1% x (75M - 100K) = EUR 749,000
# Live Service: 1% x (15M - 100K) = EUR 149,000/yr (recurring)
ROYALTY_PER_GAME_BY_TIER: Dict[StudioTier, float] = {
    StudioTier.INDIE: 4_000,
    StudioTier.AA: 99_000,
    StudioTier.AAA: 749_000,
    StudioTier.LIVE_SERVICE: 149_000,
}

# SLA attach rates by studio tier (fraction that buy Premium 24/7 SLA)
SLA_ATTACH_RATE: Dict[StudioTier, float] = {
    StudioTier.INDIE: 0.05,
    StudioTier.AA: 0.25,
    StudioTier.AAA: 0.40,
    StudioTier.LIVE_SERVICE: 0.15,
}


# ---------------------------------------------------------------------------
# Inflation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InflationConfig:
    general_rate: float = 0.03          # 3% annual inflation on non-personnel OpEx
    # Categories that inflate:
    # office rent, insurance, legal, hardware, training, accounting, out-of-pocket, contingency
    # Categories that do NOT inflate (already handled separately):
    # marketing budgets (set per year in arrays), hosting (tech deflation), GPU cloud


# ---------------------------------------------------------------------------
# OpEx
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OpExConfig:
    # --- Software & Tools ---
    software_base_monthly: float = 55.0         # per head: GitHub, Slack, Notion, Figma
    software_ai_tools_monthly: float = 200.0    # base: W&B, HuggingFace Pro, vector DB SaaS, etc.
    software_ai_per_rd_head: float = 50.0       # additional per R&D head for AI tooling

    travel_pct_of_salaries: float = 0.10
    contingency_pct: float = 0.10

    # --- Office ---
    office_costs: Dict[str, float] = field(default_factory=lambda: {
        "Amsterdam": 6_000,
        "Atlanta": 4_200,
        "Jakarta": 2_400,
        "Saigon": 1_800,
    })
    office_schedule: Dict[str, int] = field(default_factory=lambda: {
        "Amsterdam": 12,    # 2027
        "Atlanta": 24,      # 2028
        "Jakarta": 36,      # 2029
        "Saigon": 36,       # 2029
    })

    # --- Insurance ---
    insurance_base: float = 4_000               # per year, small team
    insurance_per_head: float = 500             # per head per year

    # --- Legal ---
    legal_base: float = 10_000                  # per year
    legal_growth_rate: float = 0.30             # 30% annual growth

    # --- Hardware (workstations, NOT GPU) ---
    workstation_per_hire: float = 2_000         # laptop per new hire
    hardware_ongoing_per_head: float = 100.0    # monthly per head (peripherals, replacements)

    # --- Training & Education ---
    training_per_head_annual: float = 1_000     # courses, certs, books, non-marketing conferences

    # --- Out-of-Pocket / Miscellaneous ---
    oop_base_monthly: float = 500.0             # domain names, bank fees, KvK, notary, small purchases

    # --- Sales Commission ---
    sales_commission_rate: float = 0.10    # 10% commission on direct B2B sales-sourced revenue

    # --- Accounting & Bookkeeping ---
    accounting_annual: Dict[int, float] = field(default_factory=lambda: {
        0: 6_000,     # Y1: basic bookkeeper
        1: 12_000,    # Y2: proper accountant
        2: 24_000,    # Y3+: audit-ready
        3: 24_000,
        4: 24_000,
        5: 30_000,    # Y6: growing complexity
        6: 36_000,    # Y7
        7: 42_000,    # Y8
        8: 50_000,    # Y9
        9: 60_000,    # Y10: full finance function
    })


# ---------------------------------------------------------------------------
# GPU Infrastructure (separate from hosting -- this is R&D compute)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GPUInfraConfig:
    """GPU infrastructure for model fine-tuning, benchmarking, and R&D.
    Separate from Railway hosting (which serves the production API).
    """
    # GPU hardware (CapEx -- one-time purchases, depreciable)
    # Dict: FundingScenario -> list of 10 annual CapEx budgets (Y1-Y10)
    gpu_hardware_capex: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [3_000,   0,       5_000,   5_000,   10_000,  15_000,  20_000,   25_000,   30_000,   40_000],
        FundingScenario.PRE_SEED:   [3_000,   5_000,   10_000,  15_000,  20_000,  30_000,  45_000,   60_000,   80_000,   100_000],
        FundingScenario.SEED:       [3_000,   10_000,  20_000,  30_000,  50_000,  75_000,  100_000,  140_000,  180_000,  230_000],
        FundingScenario.SERIES_A:   [3_000,   15_000,  30_000,  75_000,  120_000, 170_000, 230_000,  300_000,  400_000,  500_000],
        FundingScenario.SERIES_B:   [3_000,   15_000,  50_000,  120_000, 150_000, 200_000, 280_000,  380_000,  500_000,  650_000],
    })

    # Cloud GPU (OpEx -- monthly spend for RunPod/Lambda/etc.)
    gpu_cloud_monthly: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        #                              Y1     Y2      Y3       Y4       Y5       Y6       Y7        Y8        Y9        Y10
        FundingScenario.BOOTSTRAP:  [100,   200,    500,     1_000,   2_000,   3_500,   5_000,    7_000,    10_000,   14_000],
        FundingScenario.PRE_SEED:   [200,   500,    1_500,   3_000,   5_000,   8_000,   12_000,   18_000,   25_000,   35_000],
        FundingScenario.SEED:       [500,   1_500,  4_000,   8_000,   15_000,  22_000,  32_000,   45_000,   65_000,   90_000],
        FundingScenario.SERIES_A:   [1_000, 3_000,  8_000,   15_000,  25_000,  38_000,  55_000,   80_000,   110_000,  150_000],
        FundingScenario.SERIES_B:   [1_500, 5_000,  12_000,  25_000,  40_000,  60_000,  85_000,   120_000,  170_000,  230_000],
    })


# ---------------------------------------------------------------------------
# Marketing -- Channel-Level Budget
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EventTier:
    name: str
    cost_per_event: float
    leads_per_event: float
    lead_type: str              # "b2b_warm" or "b2c"


EVENT_TIERS: List[EventTier] = [
    EventTier("Local NL",     2_000, 10, "b2b_warm"),
    EventTier("Western EU",   5_000, 15, "b2b_warm"),
    EventTier("EU Broad",    12_000, 25, "b2b_warm"),
    EventTier("Global",      25_000, 40, "b2b_warm"),
]

# Events per year by tier, indexed by funding scenario
# Each dict maps event_tier_name -> events_per_year for model years 0-9
EVENT_SCHEDULE: Dict[FundingScenario, Dict[str, List[int]]] = {
    #                              Y1  Y2  Y3  Y4  Y5  Y6  Y7  Y8  Y9  Y10
    FundingScenario.BOOTSTRAP: {
        "Local NL":     [2, 3, 4, 4, 4, 4, 4, 4, 4, 4],
        "Western EU":   [0, 1, 1, 2, 2, 3, 3, 4, 4, 4],
        "EU Broad":     [0, 0, 0, 1, 1, 2, 2, 3, 3, 4],
        "Global":       [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
    },
    FundingScenario.PRE_SEED: {
        "Local NL":     [3, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "Western EU":   [1, 2, 3, 4, 5, 6, 6, 7, 7, 8],
        "EU Broad":     [0, 1, 2, 3, 4, 5, 6, 6, 7, 8],
        "Global":       [0, 0, 1, 2, 3, 4, 5, 6, 7, 8],
    },
    FundingScenario.SEED: {
        "Local NL":     [4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "Western EU":   [2, 3, 4, 5, 5, 6, 6, 7, 8, 8],
        "EU Broad":     [1, 2, 3, 4, 4, 5, 6, 7, 8, 8],
        "Global":       [0, 1, 2, 3, 3, 4, 5, 6, 7, 8],
    },
    FundingScenario.SERIES_A: {
        "Local NL":     [4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "Western EU":   [3, 4, 5, 5, 5, 6, 6, 7, 8, 8],
        "EU Broad":     [2, 3, 4, 4, 4, 5, 6, 7, 8, 8],
        "Global":       [1, 2, 3, 3, 3, 4, 5, 6, 7, 8],
    },
    FundingScenario.SERIES_B: {
        "Local NL":     [4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "Western EU":   [4, 5, 5, 5, 5, 6, 7, 8, 8, 8],
        "EU Broad":     [3, 4, 4, 4, 4, 5, 6, 7, 8, 8],
        "Global":       [2, 3, 3, 3, 3, 4, 5, 6, 7, 8],
    },
}


@dataclass(frozen=True)
class MarketingConfig:
    """Per-channel marketing budgets and lead generation parameters.

    Lead-generating channels connect to pipeline.py.
    Support channels are cost-only (in opex.py).
    """

    # --- Lead-generating paid channels (monthly budgets by funding scenario) ---
    # Dict: FundingScenario -> list of 10 annual budgets (Y1-Y10)
    linkedin_abm_annual: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [0,     0,      0,      0,      0,       0,       0,        0,        0,        0],
        FundingScenario.PRE_SEED:   [0,     3_000,  6_000,  12_000, 24_000,  40_000,  60_000,   85_000,   120_000,  160_000],
        FundingScenario.SEED:       [3_000, 6_000,  15_000, 30_000, 60_000,  90_000,  130_000,  180_000,  250_000,  340_000],
        FundingScenario.SERIES_A:   [6_000, 15_000, 45_000, 70_000, 100_000, 140_000, 200_000,  280_000,  380_000,  500_000],
        FundingScenario.SERIES_B:   [12_000,30_000, 70_000, 100_000,150_000, 210_000, 300_000,  420_000,  580_000,  800_000],
    })
    linkedin_abm_cost_per_lead: float = 80.0    # EUR per SQL via LinkedIn
    linkedin_abm_sql_rate: float = 0.035        # 3.5% of impressions to SQL
    linkedin_lead_type: str = "b2b_paid"

    youtube_reddit_annual: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [0,     0,      0,      0,      0,       0,       0,        0,        0,        0],
        FundingScenario.PRE_SEED:   [0,     2_000,  5_000,  12_000, 24_000,  40_000,  65_000,   100_000,  150_000,  210_000],
        FundingScenario.SEED:       [2_000, 5_000,  15_000, 33_000, 80_000,  120_000, 180_000,  260_000,  370_000,  500_000],
        FundingScenario.SERIES_A:   [5_000, 15_000, 33_000, 80_000, 150_000, 220_000, 320_000,  450_000,  620_000,  850_000],
        FundingScenario.SERIES_B:   [10_000,30_000, 60_000, 150_000,220_000, 320_000, 460_000,  650_000,  900_000,  1_250_000],
    })
    youtube_reddit_cpm: float = 12.0             # EUR per 1K views (high end of benchmark range)
    youtube_reddit_view_to_signup: float = 0.005  # 0.5% of views -> signup
    youtube_reddit_signup_to_paid: float = 0.25  # 25% of signups -> paid = ~2.5% net
    youtube_reddit_lead_type: str = "b2c_paid"

    # --- Influencer campaigns ---
    # Budget per year by scenario; campaigns are priced by tier
    influencer_annual: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [0,     0,      0,      0,      0,       0,       0,        0,        0,        0],
        FundingScenario.PRE_SEED:   [0,     2_000,  6_000,  12_000, 24_000,  40_000,  60_000,   90_000,   130_000,  180_000],
        FundingScenario.SEED:       [2_000, 6_000,  15_000, 30_000, 60_000,  90_000,  130_000,  190_000,  260_000,  360_000],
        FundingScenario.SERIES_A:   [6_000, 15_000, 40_000, 80_000, 120_000, 170_000, 240_000,  340_000,  470_000,  650_000],
        FundingScenario.SERIES_B:   [12_000,30_000, 80_000, 150_000,200_000, 280_000, 400_000,  560_000,  780_000,  1_080_000],
    })
    influencer_avg_campaign_cost: float = 2_000  # EUR (blend of micro YT + TikTok)
    influencer_avg_views_per_campaign: float = 50_000
    influencer_view_to_signup: float = 0.004     # 0.4% of views -> signup
    influencer_signup_to_paid: float = 0.30      # 30% (higher trust than ads)
    influencer_lead_type: str = "b2c_influencer"

    # --- Support channels (cost-only, no direct leads) ---
    content_production_annual: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [2_000,  4_000,  6_000,  8_000,  10_000,  13_000,  16_000,   20_000,   25_000,   30_000],
        FundingScenario.PRE_SEED:   [4_000,  8_000,  15_000, 25_000, 40_000,  60_000,  85_000,   120_000,  170_000,  230_000],
        FundingScenario.SEED:       [8_000,  15_000, 25_000, 50_000, 100_000, 150_000, 210_000,  300_000,  420_000,  580_000],
        FundingScenario.SERIES_A:   [15_000, 25_000, 50_000, 80_000, 150_000, 220_000, 310_000,  430_000,  600_000,  830_000],
        FundingScenario.SERIES_B:   [25_000, 50_000, 80_000, 120_000,200_000, 290_000, 410_000,  580_000,  800_000,  1_100_000],
    })
    # Content boosts organic growth: base 7% + content_boost
    content_organic_boost_per_1k: float = 0.002  # +0.2% organic growth per 1K/mo content spend

    community_prizes_annual: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [0,     1_000,  2_000,  4_000,  6_000,   9_000,   13_000,   18_000,   25_000,   35_000],
        FundingScenario.PRE_SEED:   [2_000, 5_000,  12_000, 25_000, 50_000,  80_000,  120_000,  180_000,  260_000,  370_000],
        FundingScenario.SEED:       [5_000, 12_000, 40_000, 80_000, 150_000, 230_000, 340_000,  500_000,  720_000,  1_000_000],
        FundingScenario.SERIES_A:   [12_000,40_000, 100_000,200_000,400_000, 600_000, 900_000,  1_300_000,1_900_000,2_700_000],
        FundingScenario.SERIES_B:   [20_000,50_000, 200_000,500_000,1_000_000,1_500_000,2_200_000,3_200_000,4_600_000,6_500_000],
    })

    graphic_design_annual: Dict[FundingScenario, List[float]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP:  [1_000, 2_000,  3_000,  5_000,  8_000,   12_000,  17_000,   24_000,   33_000,   45_000],
        FundingScenario.PRE_SEED:   [3_000, 8_000,  15_000, 30_000, 50_000,  75_000,  110_000,  160_000,  220_000,  310_000],
        FundingScenario.SEED:       [8_000, 15_000, 30_000, 60_000, 100_000, 150_000, 210_000,  300_000,  420_000,  580_000],
        FundingScenario.SERIES_A:   [15_000,30_000, 60_000, 100_000,150_000, 210_000, 300_000,  420_000,  580_000,  800_000],
        FundingScenario.SERIES_B:   [20_000,50_000, 80_000, 150_000,250_000, 360_000, 500_000,  700_000,  970_000,  1_350_000],
    })

    martech_base_monthly: float = 100.0         # base MarTech (small tools)
    martech_per_head_monthly: float = 10.0      # HubSpot/Mailchimp scales with contacts ~ headcount

    merch_per_event: float = 300.0              # swag budget per event attended

    sales_collateral_per_sales_head: float = 200.0  # monthly per sales/BD person
    outbound_tools_per_sales_head: float = 150.0     # monthly per sales/BD person


# ---------------------------------------------------------------------------
# Hosting / Infrastructure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HostingConfig:
    # Railway-based pricing
    base_monthly: float = 40.0              # 1 vCPU + 2GB (API server, DB)
    per_operation_cost: float = 0.001       # EUR per token operation (orchestration, logging, caching)
    storage_per_user_gb: float = 0.5        # vector DB storage per active user
    storage_cost_per_gb: float = 0.015      # EUR/GB/month
    egress_per_user_gb: float = 0.1         # API response egress per user/month
    egress_cost_per_gb: float = 0.05        # EUR/GB


# ---------------------------------------------------------------------------
# Expansion Revenue / NRR
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpansionConfig:
    # Profile upgrades: annual probability of moving to next tier
    upgrade_rates: Dict[str, float] = field(default_factory=lambda: {
        "solo_to_indie": 0.05,          # 5% of Solo users upgrade to Indie per year
        "indie_to_aa": 0.03,            # 3%
        "aa_to_aaa": 0.01,             # 1%
    })
    # Usage growth within tier: multiplier by year on platform
    usage_growth_by_year: List[float] = field(default_factory=lambda: [
        1.00,   # Year 1: base usage
        1.15,   # Year 2: +15%
        1.25,   # Year 3+: +25%
    ])


# ---------------------------------------------------------------------------
# Director Sales Scaling
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DirectorSalesConfig:
    base_adoption_rate: float = 0.20        # 20% passive Director adoption
    bd_active_bonus: float = 0.10           # +10% when BD is active
    per_extra_sales_bonus: float = 0.05     # +5% per sales rep beyond the first
    max_adoption_rate: float = 0.50         # cap at 50%


# ---------------------------------------------------------------------------
# Beyond-Gaming Director (World Gen / Simulation Platforms)
# ---------------------------------------------------------------------------

class BeyondGamingTier(Enum):
    STARTUP = "Startup"          # Early world gen startups, small VR training studios
    GROWTH = "Growth"            # Established sim companies, mid-size VP studios
    ENTERPRISE = "Enterprise"    # Defense primes, large VP companies, major platforms


@dataclass(frozen=True)
class BeyondGamingTierConfig:
    """Revenue and timing parameters for one beyond-gaming customer tier."""
    platform_revenue_eur: float      # Midpoint annual platform revenue
    attribution_rate: float          # % of platform revenue Director applies to
    integration_months: int          # Months from sign to live
    ramp_months: int                 # Months from live to full royalty revenue
    platform_growth_rate: float      # Annual growth rate of the platform's revenue


BEYOND_GAMING_TIERS: Dict[BeyondGamingTier, BeyondGamingTierConfig] = {
    BeyondGamingTier.STARTUP: BeyondGamingTierConfig(
        platform_revenue_eur=10_000_000,   # EUR 10M -- flat 5% royalty -> EUR 500K/yr
        attribution_rate=1.0,               # No attribution discount; royalty is on total
        integration_months=3,
        ramp_months=3,
        platform_growth_rate=0.30,          # 30% annual growth (conservative for AI startups)
    ),
    BeyondGamingTier.GROWTH: BeyondGamingTierConfig(
        platform_revenue_eur=75_000_000,   # EUR 75M -- flat 5% royalty -> EUR 3.75M/yr
        attribution_rate=1.0,               # No attribution discount; royalty is on total
        integration_months=6,
        ramp_months=6,
        platform_growth_rate=0.20,          # 20% annual growth
    ),
    BeyondGamingTier.ENTERPRISE: BeyondGamingTierConfig(
        platform_revenue_eur=1_000_000_000, # EUR 1B -- flat 5% royalty -> EUR 50M/yr
        attribution_rate=1.0,               # No attribution discount; royalty is on total
        integration_months=12,
        ramp_months=12,
        platform_growth_rate=0.10,          # 10% annual growth (mature defense/VP)
    ),
}


@dataclass(frozen=True)
class BeyondGamingConfig:
    royalty_rate: float = 0.01              # 1% — consistent with gaming Director royalty rate
    # COGS: lower than gaming (no game auditing, simpler integration)
    cogs_rate: float = 0.10                 # 10% -- payment processing + support
    # Customer acquisition schedule by tier
    # Dict: FundingScenario -> list of (model_month, BeyondGamingTier) for each new customer
    # Model month 0 = April 2026; month 12 = April 2027
    customer_schedule: Dict[FundingScenario, List[Tuple]] = field(default_factory=lambda: {
        FundingScenario.BOOTSTRAP: [],      # No beyond-gaming without funding
        FundingScenario.PRE_SEED: [
            # Y2 (2027): 3 partnerships -- 2 startups, 1 growth
            (15, BeyondGamingTier.STARTUP),     # Jul 2027
            (18, BeyondGamingTier.STARTUP),     # Oct 2027
            (20, BeyondGamingTier.GROWTH),      # Dec 2027
            # Y3 (2028): +4 -- 2 startups, 1 growth, 1 enterprise
            (26, BeyondGamingTier.STARTUP),
            (30, BeyondGamingTier.STARTUP),
            (28, BeyondGamingTier.GROWTH),
            (32, BeyondGamingTier.ENTERPRISE),
            # Y4 (2029): +5
            (38, BeyondGamingTier.STARTUP),
            (40, BeyondGamingTier.STARTUP),
            (42, BeyondGamingTier.GROWTH),
            (44, BeyondGamingTier.GROWTH),
            (46, BeyondGamingTier.ENTERPRISE),
            # Y5 (2030): +8
            (48, BeyondGamingTier.STARTUP),
            (50, BeyondGamingTier.STARTUP),
            (51, BeyondGamingTier.STARTUP),
            (52, BeyondGamingTier.GROWTH),
            (54, BeyondGamingTier.GROWTH),
            (55, BeyondGamingTier.GROWTH),
            (56, BeyondGamingTier.ENTERPRISE),
            (58, BeyondGamingTier.ENTERPRISE),
            # Y6 (2031): +9 -- accelerating ramp
            (61, BeyondGamingTier.STARTUP),
            (63, BeyondGamingTier.STARTUP),
            (65, BeyondGamingTier.STARTUP),
            (64, BeyondGamingTier.GROWTH),
            (67, BeyondGamingTier.GROWTH),
            (69, BeyondGamingTier.GROWTH),
            (66, BeyondGamingTier.ENTERPRISE),
            (70, BeyondGamingTier.ENTERPRISE),
            (71, BeyondGamingTier.STARTUP),
            # Y7 (2032): +10
            (73, BeyondGamingTier.STARTUP),
            (75, BeyondGamingTier.STARTUP),
            (77, BeyondGamingTier.STARTUP),
            (79, BeyondGamingTier.STARTUP),
            (74, BeyondGamingTier.GROWTH),
            (78, BeyondGamingTier.GROWTH),
            (80, BeyondGamingTier.GROWTH),
            (76, BeyondGamingTier.ENTERPRISE),
            (81, BeyondGamingTier.STARTUP),
            (83, BeyondGamingTier.GROWTH),
            # Y8 (2033): +11
            (85, BeyondGamingTier.STARTUP),
            (87, BeyondGamingTier.STARTUP),
            (89, BeyondGamingTier.STARTUP),
            (91, BeyondGamingTier.STARTUP),
            (86, BeyondGamingTier.GROWTH),
            (90, BeyondGamingTier.GROWTH),
            (93, BeyondGamingTier.GROWTH),
            (88, BeyondGamingTier.ENTERPRISE),
            (94, BeyondGamingTier.STARTUP),
            (92, BeyondGamingTier.GROWTH),
            (95, BeyondGamingTier.STARTUP),
            # Y9 (2034): +12
            (97, BeyondGamingTier.STARTUP),
            (99, BeyondGamingTier.STARTUP),
            (101, BeyondGamingTier.STARTUP),
            (103, BeyondGamingTier.STARTUP),
            (98, BeyondGamingTier.GROWTH),
            (102, BeyondGamingTier.GROWTH),
            (105, BeyondGamingTier.GROWTH),
            (100, BeyondGamingTier.ENTERPRISE),
            (106, BeyondGamingTier.STARTUP),
            (104, BeyondGamingTier.GROWTH),
            (107, BeyondGamingTier.STARTUP),
            (108, BeyondGamingTier.ENTERPRISE),
            # Y10 (2035): +13
            (109, BeyondGamingTier.STARTUP),
            (111, BeyondGamingTier.STARTUP),
            (113, BeyondGamingTier.STARTUP),
            (115, BeyondGamingTier.STARTUP),
            (110, BeyondGamingTier.GROWTH),
            (114, BeyondGamingTier.GROWTH),
            (117, BeyondGamingTier.GROWTH),
            (112, BeyondGamingTier.ENTERPRISE),
            (118, BeyondGamingTier.STARTUP),
            (116, BeyondGamingTier.GROWTH),
            (119, BeyondGamingTier.STARTUP),
            (113, BeyondGamingTier.ENTERPRISE),
            (117, BeyondGamingTier.GROWTH),
        ],
        FundingScenario.SEED: [
            # Same as Pre-Seed but starts 2 months earlier per tier
            (13, BeyondGamingTier.STARTUP),
            (16, BeyondGamingTier.STARTUP),
            (18, BeyondGamingTier.GROWTH),
            (24, BeyondGamingTier.STARTUP),
            (28, BeyondGamingTier.STARTUP),
            (26, BeyondGamingTier.GROWTH),
            (30, BeyondGamingTier.ENTERPRISE),
            (36, BeyondGamingTier.STARTUP),
            (38, BeyondGamingTier.STARTUP),
            (40, BeyondGamingTier.GROWTH),
            (42, BeyondGamingTier.GROWTH),
            (44, BeyondGamingTier.ENTERPRISE),
            (46, BeyondGamingTier.STARTUP),
            (48, BeyondGamingTier.STARTUP),
            (49, BeyondGamingTier.STARTUP),
            (50, BeyondGamingTier.GROWTH),
            (52, BeyondGamingTier.GROWTH),
            (53, BeyondGamingTier.GROWTH),
            (54, BeyondGamingTier.ENTERPRISE),
            (56, BeyondGamingTier.ENTERPRISE),
            # Y6 (2031): +10
            (60, BeyondGamingTier.STARTUP),
            (62, BeyondGamingTier.STARTUP),
            (64, BeyondGamingTier.STARTUP),
            (61, BeyondGamingTier.GROWTH),
            (65, BeyondGamingTier.GROWTH),
            (67, BeyondGamingTier.GROWTH),
            (63, BeyondGamingTier.ENTERPRISE),
            (68, BeyondGamingTier.ENTERPRISE),
            (66, BeyondGamingTier.STARTUP),
            (69, BeyondGamingTier.STARTUP),
            # Y7 (2032): +12
            (72, BeyondGamingTier.STARTUP),
            (74, BeyondGamingTier.STARTUP),
            (76, BeyondGamingTier.STARTUP),
            (78, BeyondGamingTier.STARTUP),
            (73, BeyondGamingTier.GROWTH),
            (77, BeyondGamingTier.GROWTH),
            (79, BeyondGamingTier.GROWTH),
            (80, BeyondGamingTier.GROWTH),
            (75, BeyondGamingTier.ENTERPRISE),
            (81, BeyondGamingTier.STARTUP),
            (82, BeyondGamingTier.STARTUP),
            (83, BeyondGamingTier.ENTERPRISE),
            # Y8 (2033): +13
            (84, BeyondGamingTier.STARTUP),
            (86, BeyondGamingTier.STARTUP),
            (88, BeyondGamingTier.STARTUP),
            (90, BeyondGamingTier.STARTUP),
            (92, BeyondGamingTier.STARTUP),
            (85, BeyondGamingTier.GROWTH),
            (89, BeyondGamingTier.GROWTH),
            (91, BeyondGamingTier.GROWTH),
            (93, BeyondGamingTier.GROWTH),
            (87, BeyondGamingTier.ENTERPRISE),
            (94, BeyondGamingTier.STARTUP),
            (95, BeyondGamingTier.ENTERPRISE),
            (93, BeyondGamingTier.GROWTH),
            # Y9 (2034): +14
            (96, BeyondGamingTier.STARTUP),
            (98, BeyondGamingTier.STARTUP),
            (100, BeyondGamingTier.STARTUP),
            (102, BeyondGamingTier.STARTUP),
            (104, BeyondGamingTier.STARTUP),
            (97, BeyondGamingTier.GROWTH),
            (101, BeyondGamingTier.GROWTH),
            (103, BeyondGamingTier.GROWTH),
            (105, BeyondGamingTier.GROWTH),
            (106, BeyondGamingTier.GROWTH),
            (99, BeyondGamingTier.ENTERPRISE),
            (107, BeyondGamingTier.ENTERPRISE),
            (106, BeyondGamingTier.STARTUP),
            (107, BeyondGamingTier.STARTUP),
            # Y10 (2035): +16
            (108, BeyondGamingTier.STARTUP),
            (110, BeyondGamingTier.STARTUP),
            (112, BeyondGamingTier.STARTUP),
            (114, BeyondGamingTier.STARTUP),
            (116, BeyondGamingTier.STARTUP),
            (118, BeyondGamingTier.STARTUP),
            (109, BeyondGamingTier.GROWTH),
            (113, BeyondGamingTier.GROWTH),
            (115, BeyondGamingTier.GROWTH),
            (117, BeyondGamingTier.GROWTH),
            (119, BeyondGamingTier.GROWTH),
            (111, BeyondGamingTier.ENTERPRISE),
            (116, BeyondGamingTier.ENTERPRISE),
            (119, BeyondGamingTier.ENTERPRISE),
            (118, BeyondGamingTier.STARTUP),
            (119, BeyondGamingTier.STARTUP),
        ],
        FundingScenario.SERIES_A: [
            (12, BeyondGamingTier.STARTUP),
            (14, BeyondGamingTier.STARTUP),
            (16, BeyondGamingTier.GROWTH),
            (22, BeyondGamingTier.STARTUP),
            (26, BeyondGamingTier.STARTUP),
            (24, BeyondGamingTier.GROWTH),
            (28, BeyondGamingTier.ENTERPRISE),
            (34, BeyondGamingTier.STARTUP),
            (36, BeyondGamingTier.STARTUP),
            (38, BeyondGamingTier.GROWTH),
            (40, BeyondGamingTier.GROWTH),
            (42, BeyondGamingTier.ENTERPRISE),
            (44, BeyondGamingTier.STARTUP),
            (46, BeyondGamingTier.STARTUP),
            (47, BeyondGamingTier.STARTUP),
            (48, BeyondGamingTier.GROWTH),
            (50, BeyondGamingTier.GROWTH),
            (51, BeyondGamingTier.GROWTH),
            (52, BeyondGamingTier.ENTERPRISE),
            (54, BeyondGamingTier.ENTERPRISE),
            # Y6 (2031): +11
            (60, BeyondGamingTier.STARTUP),
            (62, BeyondGamingTier.STARTUP),
            (64, BeyondGamingTier.STARTUP),
            (66, BeyondGamingTier.STARTUP),
            (61, BeyondGamingTier.GROWTH),
            (65, BeyondGamingTier.GROWTH),
            (67, BeyondGamingTier.GROWTH),
            (68, BeyondGamingTier.GROWTH),
            (63, BeyondGamingTier.ENTERPRISE),
            (69, BeyondGamingTier.ENTERPRISE),
            (70, BeyondGamingTier.STARTUP),
            # Y7 (2032): +13
            (72, BeyondGamingTier.STARTUP),
            (74, BeyondGamingTier.STARTUP),
            (76, BeyondGamingTier.STARTUP),
            (78, BeyondGamingTier.STARTUP),
            (80, BeyondGamingTier.STARTUP),
            (73, BeyondGamingTier.GROWTH),
            (77, BeyondGamingTier.GROWTH),
            (79, BeyondGamingTier.GROWTH),
            (81, BeyondGamingTier.GROWTH),
            (75, BeyondGamingTier.ENTERPRISE),
            (82, BeyondGamingTier.ENTERPRISE),
            (83, BeyondGamingTier.STARTUP),
            (83, BeyondGamingTier.GROWTH),
            # Y8 (2033): +15
            (84, BeyondGamingTier.STARTUP),
            (86, BeyondGamingTier.STARTUP),
            (88, BeyondGamingTier.STARTUP),
            (90, BeyondGamingTier.STARTUP),
            (92, BeyondGamingTier.STARTUP),
            (94, BeyondGamingTier.STARTUP),
            (85, BeyondGamingTier.GROWTH),
            (89, BeyondGamingTier.GROWTH),
            (91, BeyondGamingTier.GROWTH),
            (93, BeyondGamingTier.GROWTH),
            (95, BeyondGamingTier.GROWTH),
            (87, BeyondGamingTier.ENTERPRISE),
            (94, BeyondGamingTier.ENTERPRISE),
            (95, BeyondGamingTier.STARTUP),
            (95, BeyondGamingTier.GROWTH),
            # Y9 (2034): +17
            (96, BeyondGamingTier.STARTUP),
            (98, BeyondGamingTier.STARTUP),
            (100, BeyondGamingTier.STARTUP),
            (102, BeyondGamingTier.STARTUP),
            (104, BeyondGamingTier.STARTUP),
            (106, BeyondGamingTier.STARTUP),
            (97, BeyondGamingTier.GROWTH),
            (101, BeyondGamingTier.GROWTH),
            (103, BeyondGamingTier.GROWTH),
            (105, BeyondGamingTier.GROWTH),
            (107, BeyondGamingTier.GROWTH),
            (107, BeyondGamingTier.GROWTH),
            (99, BeyondGamingTier.ENTERPRISE),
            (106, BeyondGamingTier.ENTERPRISE),
            (107, BeyondGamingTier.ENTERPRISE),
            (105, BeyondGamingTier.STARTUP),
            (107, BeyondGamingTier.STARTUP),
            # Y10 (2035): +19
            (108, BeyondGamingTier.STARTUP),
            (110, BeyondGamingTier.STARTUP),
            (112, BeyondGamingTier.STARTUP),
            (114, BeyondGamingTier.STARTUP),
            (116, BeyondGamingTier.STARTUP),
            (118, BeyondGamingTier.STARTUP),
            (119, BeyondGamingTier.STARTUP),
            (109, BeyondGamingTier.GROWTH),
            (113, BeyondGamingTier.GROWTH),
            (115, BeyondGamingTier.GROWTH),
            (117, BeyondGamingTier.GROWTH),
            (119, BeyondGamingTier.GROWTH),
            (119, BeyondGamingTier.GROWTH),
            (111, BeyondGamingTier.ENTERPRISE),
            (116, BeyondGamingTier.ENTERPRISE),
            (119, BeyondGamingTier.ENTERPRISE),
            (118, BeyondGamingTier.STARTUP),
            (117, BeyondGamingTier.STARTUP),
            (119, BeyondGamingTier.STARTUP),
        ],
        FundingScenario.SERIES_B: [
            (12, BeyondGamingTier.STARTUP),
            (14, BeyondGamingTier.STARTUP),
            (16, BeyondGamingTier.GROWTH),
            (22, BeyondGamingTier.STARTUP),
            (26, BeyondGamingTier.STARTUP),
            (24, BeyondGamingTier.GROWTH),
            (28, BeyondGamingTier.ENTERPRISE),
            (34, BeyondGamingTier.STARTUP),
            (36, BeyondGamingTier.STARTUP),
            (38, BeyondGamingTier.GROWTH),
            (40, BeyondGamingTier.GROWTH),
            (42, BeyondGamingTier.ENTERPRISE),
            (44, BeyondGamingTier.STARTUP),
            (46, BeyondGamingTier.STARTUP),
            (47, BeyondGamingTier.STARTUP),
            (48, BeyondGamingTier.GROWTH),
            (50, BeyondGamingTier.GROWTH),
            (51, BeyondGamingTier.GROWTH),
            (52, BeyondGamingTier.ENTERPRISE),
            (54, BeyondGamingTier.ENTERPRISE),
            # Y6 (2031): +11
            (60, BeyondGamingTier.STARTUP),
            (62, BeyondGamingTier.STARTUP),
            (64, BeyondGamingTier.STARTUP),
            (66, BeyondGamingTier.STARTUP),
            (61, BeyondGamingTier.GROWTH),
            (65, BeyondGamingTier.GROWTH),
            (67, BeyondGamingTier.GROWTH),
            (68, BeyondGamingTier.GROWTH),
            (63, BeyondGamingTier.ENTERPRISE),
            (69, BeyondGamingTier.ENTERPRISE),
            (70, BeyondGamingTier.STARTUP),
            # Y7 (2032): +13
            (72, BeyondGamingTier.STARTUP),
            (74, BeyondGamingTier.STARTUP),
            (76, BeyondGamingTier.STARTUP),
            (78, BeyondGamingTier.STARTUP),
            (80, BeyondGamingTier.STARTUP),
            (73, BeyondGamingTier.GROWTH),
            (77, BeyondGamingTier.GROWTH),
            (79, BeyondGamingTier.GROWTH),
            (81, BeyondGamingTier.GROWTH),
            (75, BeyondGamingTier.ENTERPRISE),
            (82, BeyondGamingTier.ENTERPRISE),
            (83, BeyondGamingTier.STARTUP),
            (83, BeyondGamingTier.GROWTH),
            # Y8 (2033): +15
            (84, BeyondGamingTier.STARTUP),
            (86, BeyondGamingTier.STARTUP),
            (88, BeyondGamingTier.STARTUP),
            (90, BeyondGamingTier.STARTUP),
            (92, BeyondGamingTier.STARTUP),
            (94, BeyondGamingTier.STARTUP),
            (85, BeyondGamingTier.GROWTH),
            (89, BeyondGamingTier.GROWTH),
            (91, BeyondGamingTier.GROWTH),
            (93, BeyondGamingTier.GROWTH),
            (95, BeyondGamingTier.GROWTH),
            (87, BeyondGamingTier.ENTERPRISE),
            (94, BeyondGamingTier.ENTERPRISE),
            (95, BeyondGamingTier.STARTUP),
            (95, BeyondGamingTier.GROWTH),
            # Y9 (2034): +17
            (96, BeyondGamingTier.STARTUP),
            (98, BeyondGamingTier.STARTUP),
            (100, BeyondGamingTier.STARTUP),
            (102, BeyondGamingTier.STARTUP),
            (104, BeyondGamingTier.STARTUP),
            (106, BeyondGamingTier.STARTUP),
            (97, BeyondGamingTier.GROWTH),
            (101, BeyondGamingTier.GROWTH),
            (103, BeyondGamingTier.GROWTH),
            (105, BeyondGamingTier.GROWTH),
            (107, BeyondGamingTier.GROWTH),
            (107, BeyondGamingTier.GROWTH),
            (99, BeyondGamingTier.ENTERPRISE),
            (106, BeyondGamingTier.ENTERPRISE),
            (107, BeyondGamingTier.ENTERPRISE),
            (105, BeyondGamingTier.STARTUP),
            (107, BeyondGamingTier.STARTUP),
            # Y10 (2035): +19
            (108, BeyondGamingTier.STARTUP),
            (110, BeyondGamingTier.STARTUP),
            (112, BeyondGamingTier.STARTUP),
            (114, BeyondGamingTier.STARTUP),
            (116, BeyondGamingTier.STARTUP),
            (118, BeyondGamingTier.STARTUP),
            (119, BeyondGamingTier.STARTUP),
            (109, BeyondGamingTier.GROWTH),
            (113, BeyondGamingTier.GROWTH),
            (115, BeyondGamingTier.GROWTH),
            (117, BeyondGamingTier.GROWTH),
            (119, BeyondGamingTier.GROWTH),
            (119, BeyondGamingTier.GROWTH),
            (111, BeyondGamingTier.ENTERPRISE),
            (116, BeyondGamingTier.ENTERPRISE),
            (119, BeyondGamingTier.ENTERPRISE),
            (118, BeyondGamingTier.STARTUP),
            (117, BeyondGamingTier.STARTUP),
            (119, BeyondGamingTier.STARTUP),
        ],
    })


# ---------------------------------------------------------------------------
# Tax
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaxConfig:
    innovation_box_rate: float = 0.09        # 9% (vs 25.8% standard) -- Belastingdienst
    standard_rate: float = 0.258
    use_innovation_box: bool = True


# ---------------------------------------------------------------------------
# Cash Collection Lag (months delay between accrual and cash receipt)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CollectionLagConfig:
    architect_tokens: int = 0       # Stripe charges immediately
    director_royalties: int = 1     # ~1 month average delay
    director_addons_onetime: int = 1  # invoiced Net 30
    director_sla: int = 0           # prepaid annually
    beyond_gaming: int = 2          # B2B royalty invoicing ~Net 60


# ---------------------------------------------------------------------------
# Named Team Mapping
# ---------------------------------------------------------------------------

ROLE_NAME_MAP: Dict[Role, str] = {
    Role.CEO: "Rijk Groenewoud",
    Role.CTO: "John Lewis",
    Role.ENGINE_ENGINEER: "TBD",
    Role.AI_ENGINEER: "Jesse",
    Role.BUSINESS_DEV: "Kiomi",
    Role.SUPPORT_ENGINEER: "TBD",
    Role.COMMUNITY_MANAGER: "TBD",
    Role.SALES_1: "TBD",
    Role.SALES_2: "TBD",
    Role.SALES_3: "TBD",
    Role.SALES_4: "TBD",
    Role.MARKETING_MANAGER: "TBD",
    Role.SENIOR_ENGINEER: "TBD",
    Role.DEVOPS: "TBD",
    Role.VP_SALES: "TBD",
    Role.VP_ENGINEERING: "TBD",
    Role.CFO: "TBD",
    Role.SALES_5: "TBD",
    Role.SALES_6: "TBD",
    Role.SALES_7: "TBD",
    Role.ENGINEER_3: "TBD",
    Role.ENGINEER_4: "TBD",
    Role.ENGINEER_5: "TBD",
    Role.SALES_8: "TBD",
    Role.SALES_9: "TBD",
    Role.SALES_10: "TBD",
    Role.ENGINEER_6: "TBD",
    Role.ENGINEER_7: "TBD",
    Role.SUPPORT_2: "TBD",
    Role.SUPPORT_3: "TBD",
    # Wave 5
    Role.CUSTOMER_SUCCESS_1: "TBD",
    Role.ACCOUNT_MANAGER_1: "TBD",
    Role.SOLUTIONS_ENGINEER: "TBD",
    # Wave 6
    Role.HR_MANAGER: "TBD",
    Role.OFFICE_MANAGER: "TBD",
    Role.CUSTOMER_SUCCESS_2: "TBD",
    Role.ACCOUNT_MANAGER_2: "TBD",
    Role.PRODUCT_MANAGER: "TBD",
    Role.QA_ENGINEER: "TBD",
    # Wave 7
    Role.COO: "TBD",
    Role.HEAD_OF_CS: "TBD",
    Role.DATA_ENGINEER: "TBD",
    Role.SECURITY_ENGINEER: "TBD",
    Role.TECHNICAL_WRITER: "TBD",
    # Wave 8
    Role.REGIONAL_SALES_US: "TBD",
    Role.REGIONAL_SALES_APAC: "TBD",
    Role.LEGAL_COUNSEL: "TBD",
    # Wave 9
    Role.BD_BEYOND_GAMING: "TBD",
    Role.SOLUTIONS_ARCHITECT: "TBD",
    Role.COMPLIANCE_OFFICER: "TBD",
    Role.PARTNER_MANAGER: "TBD",
}


# ---------------------------------------------------------------------------
# Valuation Multiples (ARR multiples by stage)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValuationConfig:
    arr_multiples: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "Pre-Seed": (10.0, 15.0),
        "Seed": (8.0, 12.0),
        "Series A": (10.0, 15.0),
        "Series B": (8.0, 10.0),
        "Mature": (5.0, 8.0),
    })
    exit_multiples: Tuple[float, float] = (5.0, 15.0)  # range for exit scenarios


# ---------------------------------------------------------------------------
# Cap Table
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FoundingEquity:
    shareholders: Dict[str, float] = field(default_factory=lambda: {
        "Rijk Groenewoud": 0.455,
        "John Lewis": 0.455,
        "Jesse (AI Engineer)": 0.09,        # 3% upfront + vesting 4yr, non-voting
    })
    # Non-voting holders have economic rights only -- no voting rights.
    # Founders hold all voting power. No board; founders have final say.
    non_voting: tuple = ("Jesse (AI Engineer)", "Option Pool")


# ---------------------------------------------------------------------------
# Master Config -- combines everything
# ---------------------------------------------------------------------------

@dataclass
class ModelConfig:
    funding_scenario: FundingScenario = FundingScenario.PRE_SEED
    usage_variant: UsageVariant = UsageVariant.LOW
    timing: TimingConfig = field(default_factory=TimingConfig)
    actuals: Actuals = field(default_factory=Actuals)
    token_economics: TokenEconomics = field(default_factory=TokenEconomics)
    employer_costs: EmployerCosts = field(default_factory=EmployerCosts)
    wbso: WBSOConfig = field(default_factory=WBSOConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    churn: ChurnConfig = field(default_factory=ChurnConfig)
    director: DirectorConfig = field(default_factory=DirectorConfig)
    opex: OpExConfig = field(default_factory=OpExConfig)
    inflation: InflationConfig = field(default_factory=InflationConfig)
    marketing: MarketingConfig = field(default_factory=MarketingConfig)
    gpu_infra: GPUInfraConfig = field(default_factory=GPUInfraConfig)
    hosting: HostingConfig = field(default_factory=HostingConfig)
    expansion: ExpansionConfig = field(default_factory=ExpansionConfig)
    director_sales: DirectorSalesConfig = field(default_factory=DirectorSalesConfig)
    beyond_gaming: BeyondGamingConfig = field(default_factory=BeyondGamingConfig)
    tax: TaxConfig = field(default_factory=TaxConfig)
    founding_equity: FoundingEquity = field(default_factory=FoundingEquity)
    collection_lag: CollectionLagConfig = field(default_factory=CollectionLagConfig)
    valuation: ValuationConfig = field(default_factory=ValuationConfig)

    @property
    def funding_events(self) -> List:
        return FUNDING_EVENTS[self.funding_scenario]

    @property
    def hiring_sequence(self) -> List[Tuple[Role, int]]:
        return HIRING_SEQUENCES[self.funding_scenario]

    @property
    def feature_ops(self) -> Dict[str, Dict[UserProfile, float]]:
        return FEATURE_OPS[self.usage_variant]

    @property
    def multipliers(self) -> ScenarioMultipliers:
        return SCENARIO_MULTIPLIERS[self.usage_variant]


# === END SECTION 1: CONFIGS ===


# =========================================================================
# SECTION 2: UNIT ECONOMICS
# =========================================================================

# ---------------------------------------------------------------------------
# Canonical tier order for the unit economics table
# ---------------------------------------------------------------------------

TABLE_TIERS = [
    ("solo",  UserProfile.SOLO),
    ("indie", UserProfile.INDIE),
    ("aa",    UserProfile.AA),
    ("aaa",   UserProfile.AAA),
]


# ---------------------------------------------------------------------------
# 1. Token cost per operation
# ---------------------------------------------------------------------------

def compute_token_cost_per_op(
    feature: FeatureParams,
    tier: ProjectSizeTier,
    token_econ: TokenEconomics,
) -> float:
    """
    Calculate the EUR cost of one operation of *feature* for a given *tier*.

    Returns EUR cost (float).
    """
    if feature.cost_type == "none":
        return 0.0

    # Per-token rates (EUR per 1M -> EUR per token)
    input_rate  = token_econ.input_rate_eur_per_m  / 1_000_000
    output_rate = token_econ.output_rate_eur_per_m / 1_000_000

    # Base cost: the fixed prompt + completion cost of a single AI call.
    # No overhead applied here -- base_input_tokens already reflects actual prompt size.
    base_cost = (
        feature.base_input_tokens * input_rate
        + feature.base_output_tokens * output_rate
    )

    if feature.cost_type == "fixed":
        # One call, no lore context.  e.g. Schema Generation, World Bible
        return base_cost

    if feature.cost_type == "per_chunk":
        # One AI call per lore chunk.  The "base" tokens are sent each time
        # because each chunk is processed independently (e.g. Entity Extraction).
        return tier.chunks * base_cost

    if feature.cost_type == "generation":
        # Base call + lore retrieval passes.
        # Lore context = project lore words -> tokens, plus system-prompt overhead (7%).
        lore_context_tokens = (
            tier.lore_words
            * token_econ.tokens_per_word
            * (1 + token_econ.system_prompt_overhead)
        )
        # Each lore pass sends the full context as input tokens.
        context_cost_per_pass = lore_context_tokens * input_rate
        return base_cost + feature.lore_passes * context_cost_per_pass

    raise ValueError(f"Unknown cost_type: {feature.cost_type!r}")


# ---------------------------------------------------------------------------
# 2. Revenue per operation
# ---------------------------------------------------------------------------

def compute_revenue_per_op(cost: float, markup: float) -> float:
    """Revenue = cost * markup multiplier."""
    return cost * markup


# ---------------------------------------------------------------------------
# 3. Convenience lookup
# ---------------------------------------------------------------------------

def get_revenue_per_op(
    feature_name: str,
    profile: UserProfile,
    cfg: ModelConfig,
) -> float:
    """
    Given a feature name and user profile, return the revenue per operation.
    Maps UserProfile -> ProjectSizeTier via the PROJECT_SIZE_TIERS dict.
    """
    te = cfg.token_economics
    tier = PROJECT_SIZE_TIERS[profile]

    # Find the feature by name
    feat = next((f for f in FEATURES if f.name == feature_name), None)
    if feat is None:
        raise KeyError(f"Unknown feature: {feature_name!r}")

    cost = compute_token_cost_per_op(feat, tier, te)
    return compute_revenue_per_op(cost, te.markup_multiplier)


# === END SECTION 2: UNIT ECONOMICS ===


# =========================================================================
# SECTION 3: D&A CONSTANTS + SCALING CONFIGS
# =========================================================================

# ---------------------------------------------------------------------------
# D&A Constants (from da.py)
# ---------------------------------------------------------------------------

HARDWARE_CAPEX_PER_HIRE = 2_000      # EUR one-time per new hire
HARDWARE_USEFUL_LIFE = 36            # months (3 years straight-line)
GPU_USEFUL_LIFE = 36                 # months (3 years straight-line)
DEV_COST_USEFUL_LIFE = 60            # months (5 years straight-line)
CEO_CAPITALISATION_RATE = 0.30       # 30 % of CEO gross-gross capitalised


# ---------------------------------------------------------------------------
# ScalingRoleConfig and SCALING_CONFIGS (from engine_growth.py)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScalingRoleConfig:
    """Config for generic scaling hires in a function."""
    function: str               # "sales", "support", "cs", "account_mgmt", "engineering"
    monthly_gross: float        # EUR gross salary
    is_rd: bool
    generates_leads: bool
    lead_type: str = ""
    leads_per_month: float = 0.0
    lead_conversion: float = 0.0
    manager_ratio: int = 6      # 1 manager per N direct reports
    manager_salary: float = 0.0 # Manager monthly gross (0 = no manager needed)


SCALING_CONFIGS: Dict[str, ScalingRoleConfig] = {
    "sales": ScalingRoleConfig(
        function="sales", monthly_gross=4_000, is_rd=False,
        generates_leads=True, lead_type="b2b_sales",
        leads_per_month=8, lead_conversion=0.15,
        manager_ratio=6, manager_salary=6_000,   # Sales Manager
    ),
    "support": ScalingRoleConfig(
        function="support", monthly_gross=4_000, is_rd=True,
        generates_leads=False,
        manager_ratio=6, manager_salary=6_000,   # Head of Support
    ),
    "cs": ScalingRoleConfig(
        function="cs", monthly_gross=4_500, is_rd=False,
        generates_leads=False,
        manager_ratio=8, manager_salary=6_500,   # CS Director
    ),
    "account_mgmt": ScalingRoleConfig(
        function="account_mgmt", monthly_gross=5_000, is_rd=False,
        generates_leads=True, lead_type="b2b_warm",
        leads_per_month=3, lead_conversion=0.20,
        manager_ratio=8, manager_salary=7_000,   # Head of Accounts
    ),
    "platform_eng": ScalingRoleConfig(
        function="platform_eng", monthly_gross=5_000, is_rd=True,
        generates_leads=False,
        manager_ratio=6, manager_salary=7_000,   # Engineering Manager
    ),
    "research": ScalingRoleConfig(
        function="research", monthly_gross=12_000, is_rd=True,
        generates_leads=False,
        manager_ratio=5, manager_salary=15_000,  # Research Lead / Principal Researcher
    ),
    "devops": ScalingRoleConfig(
        function="devops", monthly_gross=5_500, is_rd=True,
        generates_leads=False,
        manager_ratio=8, manager_salary=7_000,   # Infra Lead
    ),
    "qa": ScalingRoleConfig(
        function="qa", monthly_gross=4_500, is_rd=True,
        generates_leads=False,
        manager_ratio=8, manager_salary=6_000,   # QA Lead
    ),
    "bg_bd": ScalingRoleConfig(
        function="bg_bd", monthly_gross=6_000, is_rd=False,
        generates_leads=False,  # leads handled in beyond-gaming logic
        manager_ratio=6, manager_salary=8_000,
    ),
    "bg_solutions": ScalingRoleConfig(
        function="bg_solutions", monthly_gross=7_000, is_rd=True,
        generates_leads=False,
        manager_ratio=6, manager_salary=8_000,
    ),
}


# === END SECTION 3: D&A CONSTANTS + SCALING CONFIGS ===


# =========================================================================
# SECTION 4: REVENUE FUNCTIONS
# =========================================================================

# Director COGS rates -- mirrors director_rev.py exactly
_PAYMENT_PROCESSING_RATE = 0.029
_ROYALTY_AUDIT_RATE = 0.01
_ROYALTY_ENGINEERING_RATE = 0.01
_ROYALTY_SUPPORT_RATE = 0.10
_ADDON_ONETIME_COGS_RATE = 0.35
_ADDON_SUPPORT_RATE = 0.10
_SLA_COGS_RATE = 0.70

# SLA price (annual) -- same lookup as director_pipeline.py
_SLA_ADDON_PRICE = next(a.price for a in DIRECTOR_ADDONS if a.name == "Premium 24/7 SLA")

# Director tiers tracked in the pipeline (same as director_pipeline.py)
_DIRECTOR_TIERS: List[StudioTier] = [StudioTier.INDIE, StudioTier.AA, StudioTier.AAA]


# ---------------------------------------------------------------------------
# Helper: usage multiplier (identical to architect_rev._usage_multiplier)
# ---------------------------------------------------------------------------

def _usage_multiplier(tenure_months: float, usage_growth_by_year: list) -> float:
    """Map average tenure (months) to a usage multiplier via linear interpolation.

    usage_growth_by_year is e.g. [1.0, 1.15, 1.25] meaning:
        Year 0 on platform -> 1.0x
        Year 1 -> 1.15x
        Year 2+ -> 1.25x
    """
    year_on_platform = tenure_months / 12.0
    max_idx = len(usage_growth_by_year) - 1
    year_on_platform = min(year_on_platform, float(max_idx))

    year_idx = int(year_on_platform)
    frac = year_on_platform - year_idx

    if year_idx >= max_idx:
        return usage_growth_by_year[-1]
    return (usage_growth_by_year[year_idx]
            + frac * (usage_growth_by_year[year_idx + 1]
                      - usage_growth_by_year[year_idx]))


# ---------------------------------------------------------------------------
# Function 1: Architect token revenue for one month
# ---------------------------------------------------------------------------

def compute_architect_revenue_month(
    cfg: ModelConfig,
    active_customers: Dict[UserProfile, float],
    tenure_months: Dict[UserProfile, float],
    month: int,
) -> dict:
    """Compute Architect token revenue for one month.

    Uses the exact same formulas as build_architect_revenue in architect_rev.py:
      - Revenue per op = cost per op x markup (locked at year-0 prices, never deflated)
      - Token cost deflates 20%/yr (compounding) as AI costs drop
      - Payment processing = gross revenue x payment_processing_rate

    Parameters
    ----------
    cfg : ModelConfig
        Master config with all assumptions.
    active_customers : dict
        {UserProfile: active_user_count} for this month.
    tenure_months : dict
        {UserProfile: average_tenure_in_months} for this month.
        Used to compute the usage growth multiplier.
    month : int
        Calendar month index (0-based). Used for AI cost deflation.

    Returns
    -------
    dict with keys:
        gross_revenue, token_cost, payment_processing, net_revenue,
        per_profile_revenue (dict of UserProfile -> float)
    """
    te = cfg.token_economics
    feature_ops = cfg.feature_ops  # usage-variant-selected ops table
    usage_growth = cfg.expansion.usage_growth_by_year

    # AI cost deflation: costs drop ai_cost_deflation_per_year per year, compounding
    cost_deflation = (1 - te.ai_cost_deflation_per_year) ** (month / 12)
    # Price deflation: pass half the cost savings to customers as lower prices
    price_deflation = (1 - te.ai_cost_deflation_per_year * 0.5) ** (month / 12)

    gross_revenue = 0.0
    token_cost = 0.0
    per_profile_revenue: Dict[UserProfile, float] = {}

    for profile in UserProfile:
        users = active_customers.get(profile, 0.0)
        if users <= 0:
            per_profile_revenue[profile] = 0.0
            continue

        # Usage multiplier from average tenure
        ten = tenure_months.get(profile, 0.0)
        mult = _usage_multiplier(ten, usage_growth)

        profile_rev = 0.0
        profile_cost = 0.0

        for feat_name in FEATURE_NAMES:
            ops_per_user = feature_ops[feat_name][profile]
            if ops_per_user == 0:
                continue

            ops_total = users * ops_per_user * mult

            # Revenue: deflated at half the rate of cost deflation
            rev_per_op = get_revenue_per_op(feat_name, profile, cfg)
            profile_rev += ops_total * rev_per_op * price_deflation

            # Cost: fully deflated by AI cost reduction
            tier = PROJECT_SIZE_TIERS[profile]
            feat = next(f for f in FEATURES if f.name == feat_name)
            cost_per_op = compute_token_cost_per_op(feat, tier, te)
            profile_cost += ops_total * cost_per_op * cost_deflation

        per_profile_revenue[profile] = profile_rev
        gross_revenue += profile_rev
        token_cost += profile_cost

    payment_processing = gross_revenue * te.payment_processing_rate
    net_revenue = gross_revenue - payment_processing

    return {
        "gross_revenue": gross_revenue,
        "token_cost": token_cost,
        "payment_processing": payment_processing,
        "net_revenue": net_revenue,
        "per_profile_revenue": per_profile_revenue,
    }


# ---------------------------------------------------------------------------
# Function 2: Director gaming revenue for one month
# ---------------------------------------------------------------------------

def compute_director_gaming_month(
    cfg: ModelConfig,
    director_state: dict,
    new_b2b_closed: float,
    adoption_rate: float,
    month: int,
) -> Tuple[dict, dict]:
    """Compute Director gaming revenue for one month.

    Uses the exact same formulas as build_director_pipeline and
    build_director_revenue (director_pipeline.py, director_rev.py).

    Parameters
    ----------
    cfg : ModelConfig
        Master config with all assumptions.
    director_state : dict
        Mutable state tracking Director pipeline. Keys:
            cum_studios: {StudioTier: float}  -- cumulative studios signed
            pending_games: list of (ship_month, StudioTier, count)
            cum_sla_studios: {StudioTier: float}  -- cumulative SLA studios
        Pass an empty dict on the first call; this function initialises it.
    new_b2b_closed : float
        Total new B2B deals closed this month (before Director conversion).
    adoption_rate : float
        Director adoption rate for this month (from _director_adoption_rate).
    month : int
        Calendar month index (0-based).

    Returns
    -------
    (revenue_dict, updated_director_state)
    revenue_dict keys:
        royalty, addon_onetime, addon_sla, total,
        cogs_royalty, cogs_addon_onetime, cogs_addon_sla, cogs_total,
        new_studios_total, architect_crosssell
    """
    dcfg = cfg.director
    pipe = cfg.pipeline
    tier_split = pipe.b2b_tier_split

    # Initialise state on first call
    if "cum_studios" not in director_state:
        director_state["cum_studios"] = {t: 0.0 for t in _DIRECTOR_TIERS}
        director_state["pending_games"] = []
        director_state["cum_sla_studios"] = {t: 0.0 for t in _DIRECTOR_TIERS}

    # --- New Director studios this month ---
    director_new_total = new_b2b_closed * adoption_rate
    new_studios: Dict[StudioTier, float] = {}
    for tier in _DIRECTOR_TIERS:
        new_studios[tier] = director_new_total * tier_split[tier]

    new_studios_total = sum(new_studios.values())

    # --- Update cumulative studios ---
    for tier in _DIRECTOR_TIERS:
        director_state["cum_studios"][tier] += new_studios[tier]

    # --- Schedule game shipments ---
    for tier in _DIRECTOR_TIERS:
        if new_studios[tier] > 0:
            cycle = dcfg.dev_cycle_months[tier]
            ship_month = month + cycle
            director_state["pending_games"].append(
                (ship_month, tier, new_studios[tier])
            )

    # --- Games shipping this month ---
    games_shipping: Dict[StudioTier, float] = {t: 0.0 for t in _DIRECTOR_TIERS}
    remaining_pending = []
    for ship_month, tier, count in director_state["pending_games"]:
        if ship_month == month:
            games_shipping[tier] += count
        else:
            remaining_pending.append((ship_month, tier, count))
    director_state["pending_games"] = remaining_pending

    # --- Royalty revenue ---
    royalty = 0.0
    for tier in _DIRECTOR_TIERS:
        royalty += games_shipping[tier] * ROYALTY_PER_GAME_BY_TIER[tier]

    # --- Add-on one-time revenue (at sign-up) ---
    addon_onetime = 0.0
    for tier in _DIRECTOR_TIERS:
        attach = ADDON_ATTACH_RATES[tier]
        avg_spend = ADDON_AVG_SPEND[tier]
        addon_onetime += new_studios[tier] * attach * avg_spend

    # --- SLA recurring revenue ---
    for tier in _DIRECTOR_TIERS:
        director_state["cum_sla_studios"][tier] += (
            new_studios[tier] * SLA_ATTACH_RATE[tier]
        )

    addon_sla = 0.0
    for tier in _DIRECTOR_TIERS:
        addon_sla += director_state["cum_sla_studios"][tier] * (_SLA_ADDON_PRICE / 12)

    total_rev = royalty + addon_onetime + addon_sla

    # --- COGS (mirrors director_rev.py exactly) ---
    pp = _PAYMENT_PROCESSING_RATE
    cogs_royalty = royalty * (pp + _ROYALTY_AUDIT_RATE + _ROYALTY_ENGINEERING_RATE + _ROYALTY_SUPPORT_RATE)
    cogs_addon_onetime = addon_onetime * (_ADDON_ONETIME_COGS_RATE + pp + _ADDON_SUPPORT_RATE)
    cogs_addon_sla = addon_sla * _SLA_COGS_RATE
    cogs_total = cogs_royalty + cogs_addon_onetime + cogs_addon_sla

    # --- Architect cross-sell ---
    architect_crosssell = new_studios_total * pipe.director_to_architect_crosssell

    revenue_dict = {
        "royalty": royalty,
        "addon_onetime": addon_onetime,
        "addon_sla": addon_sla,
        "total": total_rev,
        "cogs_royalty": cogs_royalty,
        "cogs_addon_onetime": cogs_addon_onetime,
        "cogs_addon_sla": cogs_addon_sla,
        "cogs_total": cogs_total,
        "new_studios_total": new_studios_total,
        "architect_crosssell": architect_crosssell,
    }

    return revenue_dict, director_state


# ---------------------------------------------------------------------------
# Function 3: Beyond-gaming revenue for one month
# ---------------------------------------------------------------------------

def compute_beyond_gaming_month(
    cfg: ModelConfig,
    bg_state: dict,
    bg_bd_count: int,
    bg_solutions_count: int,
    month: int,
    bg_bd_first_month: int = -1,
) -> Tuple[dict, dict]:
    """Compute beyond-gaming revenue for one month, driven by team capacity.

    Bottom-up model: BD people close deals, solutions architects integrate
    them, revenue flows from active partnerships as a 5% royalty on partner
    platform revenue.

    Customer tiers:
        Startup:    EUR 10M avg platform revenue -> EUR 500K/yr royalty
        Growth:     EUR 75M avg -> EUR 3.75M/yr royalty
        Enterprise: EUR 1B avg  -> EUR 50M/yr royalty

    Integration time: Startup 6mo, Growth 12mo, Enterprise 18mo.
    Partner platform revenue grows ~25%/yr from sign date.

    Parameters
    ----------
    cfg : ModelConfig
        Master config with all assumptions.
    bg_state : dict
        Mutable state tracking beyond-gaming partnerships. Pass empty dict
        on first call; this function initialises it.  Keys:
            pending: [(complete_month, tier, sign_month), ...]
            active: {'Startup': int, 'Growth': int, 'Enterprise': int}
            active_sign_months: {'Startup': [m, ...], 'Growth': [...], ...}
    bg_bd_count : int
        Number of beyond-gaming BD people active this month.
    bg_solutions_count : int
        Number of solutions architects/engineers active this month.
    month : int
        Calendar month index (0-based).

    Returns
    -------
    (revenue_dict, updated_bg_state)
    revenue_dict keys: revenue, cogs, new_partners, active_partners
    """
    bg = cfg.beyond_gaming
    cogs_rate = bg.cogs_rate

    # --- Tier parameters ---
    _TIERS = ("Startup", "Growth", "Enterprise")
    _TIER_AVG_REVENUE = {  # Annual platform revenue per partner
        "Startup": 10_000_000,
        "Growth": 75_000_000,
        "Enterprise": 1_000_000_000,
    }
    _ROYALTY_RATE = 0.05
    _INTEGRATION_MONTHS = {"Startup": 6, "Growth": 12, "Enterprise": 18}
    _TIER_SPLIT = {"Startup": 0.70, "Growth": 0.25, "Enterprise": 0.05}
    _PARTNER_GROWTH_RATE = 0.25  # 25%/yr platform revenue growth
    _DEALS_PER_BD_PER_MONTH = 0.3  # ~3-4 deals/yr blended
    _MAX_INTEGRATIONS_PER_SA = 5  # solutions architect capacity

    # --- Initialise state on first call ---
    if "pending" not in bg_state:
        bg_state["pending"] = []
        bg_state["active"] = {t: 0 for t in _TIERS}
        bg_state["active_sign_months"] = {t: [] for t in _TIERS}

    # --- Effective BD capacity (9-month ramp period) ---
    # Each BD person needs 9 months to build pipeline before closing deals.
    # Approximate: ramp linearly from first BD hire date.
    if bg_bd_count > 0 and bg_bd_first_month >= 0:
        months_since_first_bd = month - bg_bd_first_month
        if months_since_first_bd <= 0:
            effective_bd = 0.0
        elif months_since_first_bd < 9:
            effective_bd = bg_bd_count * (months_since_first_bd / 9.0)
        else:
            effective_bd = float(bg_bd_count)
    else:
        effective_bd = 0.0

    # --- New deals from BD capacity ---
    new_deals_total = effective_bd * _DEALS_PER_BD_PER_MONTH
    new_partners_total = 0

    for tier in _TIERS:
        new_deals_tier = new_deals_total * _TIER_SPLIT[tier]
        if new_deals_tier > 0:
            integration_time = _INTEGRATION_MONTHS[tier]
            complete_month = month + integration_time
            bg_state["pending"].append((complete_month, tier, month))
            new_partners_total += new_deals_tier

    # --- Complete integrations (move pending -> active) ---
    remaining_pending = []
    for complete_m, tier, sign_m in bg_state["pending"]:
        if complete_m <= month:
            bg_state["active"][tier] += 1
            bg_state["active_sign_months"][tier].append(sign_m)
        else:
            remaining_pending.append((complete_m, tier, sign_m))
    bg_state["pending"] = remaining_pending

    # --- Cap active partners by solutions architect capacity ---
    max_active = bg_solutions_count * _MAX_INTEGRATIONS_PER_SA
    total_active = sum(bg_state["active"].values())
    if total_active > max_active and max_active >= 0:
        # Scale down proportionally (can't support more than capacity)
        if total_active > 0:
            scale = max_active / total_active
            for tier in _TIERS:
                bg_state["active"][tier] = int(bg_state["active"][tier] * scale)

    # --- Revenue from active partners ---
    revenue = 0.0
    for tier in _TIERS:
        count = bg_state["active"][tier]
        if count <= 0:
            continue
        # Each active partner generates royalty; account for platform growth
        # Use average growth across all active partners of this tier
        sign_months = bg_state["active_sign_months"][tier]
        tier_revenue = 0.0
        for sm in sign_months[-count:]:  # use most recent 'count' sign months
            months_since_sign = max(0, month - sm)
            growth_factor = (1 + _PARTNER_GROWTH_RATE) ** (months_since_sign / 12)
            annual_royalty = _TIER_AVG_REVENUE[tier] * _ROYALTY_RATE * growth_factor
            tier_revenue += annual_royalty / 12  # monthly
        revenue += tier_revenue

    total_active_partners = sum(bg_state["active"].values())
    cogs = revenue * cogs_rate

    return {
        "revenue": revenue,
        "cogs": cogs,
        "new_partners": new_partners_total,
        "active_partners": total_active_partners,
    }, bg_state


# ---------------------------------------------------------------------------
# Function 4: Consolidated COGS for one month
# ---------------------------------------------------------------------------

def compute_cogs_month(
    cfg: ModelConfig,
    architect_gross_rev: float,
    architect_token_cost: float,
    architect_payment_proc: float,
    total_active_users: float,
    director_rev: dict,
    beyond_gaming_rev: float,
    month: int,
    total_revenue: float = 0.0,
) -> dict:
    """Compute total COGS for one month.

    Uses the exact same formulas as build_cogs in cogs.py.

    Parameters
    ----------
    cfg : ModelConfig
        Master config with all assumptions.
    architect_gross_rev : float
        Architect gross revenue for this month.
    architect_token_cost : float
        Architect token (AI API) cost for this month (already deflated).
    architect_payment_proc : float
        Architect payment processing cost for this month.
    total_active_users : float
        Total active Architect users across all profiles.
    director_rev : dict
        Output from compute_director_gaming_month (needs cogs_total key).
    beyond_gaming_rev : float
        Beyond-gaming COGS for this month.
    month : int
        Calendar month index (0-based).

    Returns
    -------
    dict with keys:
        token_costs, payment_processing, hosting,
        architect_subtotal, director_cogs, beyond_gaming_cogs, total
    """
    h = cfg.hosting

    # --- Hosting: compute-based (Railway pricing model) ---
    # Approximate total operations from gross revenue / markup -> cost, then / ~1.5 avg cost per op
    token_cost_proxy = architect_gross_rev / cfg.token_economics.markup_multiplier
    approx_total_ops = token_cost_proxy / 1.5  # avg ~1.5 EUR per op from unit economics

    hosting = (
        h.base_monthly
        + approx_total_ops * h.per_operation_cost
        + total_active_users * h.storage_per_user_gb * h.storage_cost_per_gb
        + total_active_users * h.egress_per_user_gb * h.egress_cost_per_gb
    )

    # --- Architect subtotal ---
    architect_subtotal = architect_token_cost + architect_payment_proc + hosting

    # --- Director COGS ---
    director_cogs = director_rev.get("cogs_total", 0.0)

    # --- Beyond-gaming COGS ---
    beyond_gaming_cogs = beyond_gaming_rev

    # --- Currency exchange: applies to all revenue (international payments) ---
    fx_cost = total_revenue * cfg.token_economics.fx_exchange_cost_rate

    # --- Total ---
    total = architect_subtotal + director_cogs + beyond_gaming_cogs + fx_cost

    return {
        "token_costs": architect_token_cost,
        "payment_processing": architect_payment_proc,
        "hosting": hosting,
        "architect_subtotal": architect_subtotal,
        "director_cogs": director_cogs,
        "beyond_gaming_cogs": beyond_gaming_cogs,
        "fx_cost": fx_cost,
        "total": total,
    }


# === END SECTION 4: REVENUE FUNCTIONS ===


# =========================================================================
# SECTION 5: COST FUNCTIONS
# =========================================================================

# ---------------------------------------------------------------------------
# Sales / BD role set (mirrors opex.py)
# ---------------------------------------------------------------------------

_SALES_BD_ROLES: frozenset = frozenset({
    Role.BUSINESS_DEV,
    Role.SALES_1, Role.SALES_2, Role.SALES_3, Role.SALES_4,
    Role.SALES_5, Role.SALES_6, Role.SALES_7, Role.SALES_8,
    Role.SALES_9, Role.SALES_10, Role.VP_SALES,
})


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fte_fraction(role: Role, month: int) -> float:
    """Return the FTE fraction for a role at a given month.

    Roles not in FTE_SCHEDULE are 1.0 (full-time).
    For roles with a schedule, use the latest entry whose month <= current month.
    """
    if role not in FTE_SCHEDULE:
        return 1.0
    schedule = FTE_SCHEDULE[role]
    fte = 1.0
    for from_month, fraction in schedule:
        if month >= from_month:
            fte = fraction
    return fte


def _base_salary(role: Role, rc: RoleConfig, month: int) -> float:
    """Return the base monthly gross for a role at a given month.

    Uses SALARY_OVERRIDE if the role has one, otherwise falls back to
    RoleConfig.monthly_gross.
    """
    if role not in SALARY_OVERRIDE:
        return rc.monthly_gross
    schedule = SALARY_OVERRIDE[role]
    base = rc.monthly_gross
    for from_month, amount in schedule:
        if month >= from_month:
            base = amount
    return base


def _salary_multiplier(month: int) -> float:
    """Compute cumulative salary multiplier with step-down schedule.

    Uses SALARY_INCREASE_SCHEDULE: 10% Y1-Y3, 5% Y4+ (catch-up then market).
    Applied as monthly compounding for smooth growth.
    """
    multiplier = 1.0
    for m in range(month):
        rate = SALARY_INCREASE_SCHEDULE[0][1]  # default to first rate
        for threshold_month, r in SALARY_INCREASE_SCHEDULE:
            if m >= threshold_month:
                rate = r
        multiplier *= (1 + rate) ** (1 / 12)
    return multiplier


def _annual_budget_monthly(
    annual_by_scenario: Dict[FundingScenario, list],
    scenario: FundingScenario,
    year: int,
) -> float:
    """Look up an annual budget for (scenario, year) and return monthly."""
    yearly_list = annual_by_scenario.get(scenario, [0] * 10)
    yr = min(year, len(yearly_list) - 1)
    return yearly_list[yr] / 12.0


# ---------------------------------------------------------------------------
# Function 1: Personnel
# ---------------------------------------------------------------------------

def compute_personnel_month(
    cfg: ModelConfig,
    active_named_roles: Set[Role],
    scaling_hires: Dict[str, int],
    scaling_managers: Dict[str, int],
    month: int,
) -> dict:
    """Compute personnel costs for one month.

    Parameters
    ----------
    cfg : ModelConfig
        Full model configuration.
    active_named_roles : Set[Role]
        The named roles that are active this month.
    scaling_hires : Dict[str, int]
        Generic scaling hires per function (e.g. {"sales": 3, "support": 2}).
    scaling_managers : Dict[str, int]
        Managers added per function (e.g. {"sales": 1}).
    month : int
        Zero-based model month.

    Returns
    -------
    dict with keys:
        total_headcount, total_gross_salary, total_gross_gross,
        total_wbso_benefit, total_net_cost,
        rd_headcount, sales_headcount,
        rd_gross_gross, ceo_gross_gross
    """
    employer_rate = cfg.employer_costs.total_rate      # ~0.38
    wbso_rate = cfg.wbso.effective_reduction           # ~0.30
    multiplier = _salary_multiplier(month)

    total_headcount = 0.0
    total_gross_salary = 0.0
    total_gross_gross = 0.0
    total_wbso_benefit = 0.0
    total_net_cost = 0.0
    rd_headcount = 0.0
    sales_headcount = 0.0
    rd_gross_gross = 0.0
    ceo_gross_gross = 0.0

    # --- Named roles ---
    for rc in ROLE_CONFIGS:
        if rc.role not in active_named_roles:
            continue

        fte = _fte_fraction(rc.role, month)
        base = _base_salary(rc.role, rc, month)
        gross = base * multiplier * fte
        gg = gross * (1 + employer_rate)
        wbso = gg * wbso_rate if rc.is_rd else 0.0
        net = gg - wbso

        total_headcount += fte
        total_gross_salary += gross
        total_gross_gross += gg
        total_wbso_benefit += wbso
        total_net_cost += net

        if rc.is_rd:
            rd_headcount += fte
            rd_gross_gross += gg
        if rc.role in _SALES_BD_ROLES:
            sales_headcount += fte
        if rc.role == Role.CEO:
            ceo_gross_gross = gg

    # --- Scaling hires (generic roles beyond named) ---
    for func, count in scaling_hires.items():
        if count <= 0:
            continue
        scfg = SCALING_CONFIGS[func]
        gross = count * scfg.monthly_gross * multiplier
        gg = gross * (1 + employer_rate)
        wbso = gg * wbso_rate if scfg.is_rd else 0.0
        net = gg - wbso

        total_headcount += count
        total_gross_salary += gross
        total_gross_gross += gg
        total_wbso_benefit += wbso
        total_net_cost += net

        if scfg.is_rd:
            rd_headcount += count
            rd_gross_gross += gg
        if scfg.function == "sales":
            sales_headcount += count

    # --- Scaling managers ---
    for func, count in scaling_managers.items():
        if count <= 0:
            continue
        scfg = SCALING_CONFIGS[func]
        if scfg.manager_salary <= 0:
            continue
        gross = count * scfg.manager_salary * multiplier
        gg = gross * (1 + employer_rate)
        wbso = gg * wbso_rate if scfg.is_rd else 0.0
        net = gg - wbso

        total_headcount += count
        total_gross_salary += gross
        total_gross_gross += gg
        total_wbso_benefit += wbso
        total_net_cost += net

        if scfg.is_rd:
            rd_headcount += count
            rd_gross_gross += gg
        if scfg.function == "sales":
            sales_headcount += count

    return {
        "total_headcount": total_headcount,
        "total_gross_salary": total_gross_salary,
        "total_gross_gross": total_gross_gross,
        "total_wbso_benefit": total_wbso_benefit,
        "total_net_cost": total_net_cost,
        "rd_headcount": rd_headcount,
        "sales_headcount": sales_headcount,
        "rd_gross_gross": rd_gross_gross,
        "ceo_gross_gross": ceo_gross_gross,
    }


# ---------------------------------------------------------------------------
# Function 2: OpEx
# ---------------------------------------------------------------------------

def compute_opex_month(
    cfg: ModelConfig,
    headcount: float,
    gross_gross: float,
    rd_headcount: float,
    sales_headcount: float,
    prev_headcount: float,
    month: int,
) -> dict:
    """Compute all OpEx categories for one month.

    Parameters
    ----------
    cfg : ModelConfig
        Full model configuration.
    headcount : float
        Total headcount this month (including fractional FTE).
    gross_gross : float
        Total gross-gross salary cost this month.
    rd_headcount : float
        R&D headcount this month.
    sales_headcount : float
        Sales/BD headcount this month.
    prev_headcount : float
        Headcount from the previous month (to compute new hires).
    month : int
        Zero-based model month.

    Returns
    -------
    dict with keys for each category + total.
    """
    ox = cfg.opex
    gpu = cfg.gpu_infra
    scenario = cfg.funding_scenario
    year = month // 12

    # Inflation factor for categories with real-cost growth
    inflation_rate = cfg.inflation.general_rate
    inflation_factor = (1 + inflation_rate) ** (month / 12)

    # --- 1. Software & Tools (NO inflation -- tech deflation) ---
    software = (headcount * ox.software_base_monthly
                + ox.software_ai_tools_monthly
                + rd_headcount * ox.software_ai_per_rd_head)

    # --- 2. Travel (NO inflation -- already % of inflating salaries) ---
    travel = gross_gross * ox.travel_pct_of_salaries

    # --- 3. Office Rent ---
    office_cities = list(ox.office_costs.keys())
    open_rates = [
        ox.office_costs[city]
        for city in office_cities
        if city in ox.office_schedule and month >= ox.office_schedule[city]
    ]
    if open_rates:
        blended_annual = sum(open_rates) / len(open_rates)
        office = headcount * blended_annual / 12.0
    else:
        office = 0.0
    office *= inflation_factor

    # --- 4. Insurance ---
    insurance = (ox.insurance_base + ox.insurance_per_head * headcount) / 12.0
    insurance *= inflation_factor

    # --- 5. Legal & Professional ---
    annual_legal = ox.legal_base * (1 + ox.legal_growth_rate) ** year
    legal = annual_legal / 12.0
    legal *= inflation_factor

    # --- 6. Hardware (workstations only -- GPU is separate) ---
    new_hires = max(0.0, headcount - prev_headcount)
    workstations = new_hires * ox.workstation_per_hire
    hardware_ongoing = headcount * ox.hardware_ongoing_per_head
    hardware = workstations + hardware_ongoing
    hardware *= inflation_factor

    # --- 7. GPU Infrastructure (NO inflation -- set per year) ---
    # GPU hardware CapEx -- lump sum in first month of each year
    gpu_hw_capex = gpu.gpu_hardware_capex[scenario]
    yr = min(year, len(gpu_hw_capex) - 1)
    gpu_capex = gpu_hw_capex[yr] if month % 12 == 0 else 0.0

    # Cloud GPU -- monthly OpEx
    gpu_cloud_monthly = gpu.gpu_cloud_monthly[scenario]
    gpu_cloud = gpu_cloud_monthly[min(year, len(gpu_cloud_monthly) - 1)]

    # --- 8. Training & Education ---
    training = headcount * ox.training_per_head_annual / 12.0
    training *= inflation_factor

    # --- 9. Out-of-Pocket / Miscellaneous ---
    oop = ox.oop_base_monthly
    oop *= inflation_factor

    # --- 10. Accounting & Bookkeeping ---
    accounting = ox.accounting_annual.get(year, ox.accounting_annual[4]) / 12.0
    accounting *= inflation_factor

    # --- 11. Marketing (11 channels) ---
    mkt = cfg.marketing
    event_sched = EVENT_SCHEDULE[scenario]
    tier_map = {t.name: t for t in EVENT_TIERS}

    events_cost = 0.0
    total_events_month = 0.0
    for tier_name, events_per_year_list in event_sched.items():
        tier = tier_map[tier_name]
        yr_e = min(year, len(events_per_year_list) - 1)
        epm = events_per_year_list[yr_e] / 12.0
        events_cost += epm * tier.cost_per_event
        total_events_month += epm

    linkedin_abm = _annual_budget_monthly(mkt.linkedin_abm_annual, scenario, year)
    youtube_reddit = _annual_budget_monthly(mkt.youtube_reddit_annual, scenario, year)
    influencer = _annual_budget_monthly(mkt.influencer_annual, scenario, year)
    content_production = _annual_budget_monthly(
        mkt.content_production_annual, scenario, year)
    community_prizes = _annual_budget_monthly(
        mkt.community_prizes_annual, scenario, year)
    graphic_design = _annual_budget_monthly(
        mkt.graphic_design_annual, scenario, year)

    martech = mkt.martech_base_monthly + mkt.martech_per_head_monthly * headcount
    merch = total_events_month * mkt.merch_per_event
    sales_collateral = sales_headcount * mkt.sales_collateral_per_sales_head
    outbound_tools = sales_headcount * mkt.outbound_tools_per_sales_head

    marketing_total = (events_cost + linkedin_abm + youtube_reddit + influencer
                       + content_production + community_prizes + graphic_design
                       + martech + merch + sales_collateral + outbound_tools)

    # --- 12. Contingency (10% of non-marketing OpEx subtotal) ---
    non_mkt_subtotal = (software + travel + office + insurance + legal
                        + hardware + training + oop + accounting + gpu_cloud)
    contingency = non_mkt_subtotal * ox.contingency_pct

    # --- OpEx total (non-marketing, including contingency) ---
    opex_total = non_mkt_subtotal + contingency

    return {
        "software": software,
        "travel": travel,
        "office": office,
        "insurance": insurance,
        "legal": legal,
        "hardware": hardware,
        "gpu_capex": gpu_capex,
        "gpu_cloud": gpu_cloud,
        "training": training,
        "oop": oop,
        "accounting": accounting,
        "marketing_events": events_cost,
        "marketing_linkedin_abm": linkedin_abm,
        "marketing_youtube_reddit": youtube_reddit,
        "marketing_influencer": influencer,
        "marketing_content_production": content_production,
        "marketing_community_prizes": community_prizes,
        "marketing_graphic_design": graphic_design,
        "marketing_martech": martech,
        "marketing_merch": merch,
        "marketing_sales_collateral": sales_collateral,
        "marketing_outbound_tools": outbound_tools,
        "marketing_total": marketing_total,
        "contingency": contingency,
        "opex_total": opex_total,
        "new_hires": new_hires,
    }


# ---------------------------------------------------------------------------
# Function 3: D&A (Depreciation & Amortization)
# ---------------------------------------------------------------------------

def compute_da_month(
    cfg: ModelConfig,
    da_state: dict,
    new_hires_this_month: float,
    gpu_capex_this_month: float,
    rd_gross_gross: float,
    ceo_gross_gross: float,
    month: int,
) -> Tuple[dict, dict]:
    """Compute D&A for one month.

    Parameters
    ----------
    cfg : ModelConfig
        Full model configuration.
    da_state : dict
        Tracks assets being depreciated. Keys:
        - "hardware_assets": list of (monthly_charge, remaining_months)
        - "gpu_assets": list of (monthly_charge, remaining_months)
        - "dev_assets": list of (monthly_charge, remaining_months)
    new_hires_this_month : float
        Number of new hires this month (for hardware CapEx).
    gpu_capex_this_month : float
        GPU CapEx placed this month.
    rd_gross_gross : float
        Total R&D gross-gross salary this month.
    ceo_gross_gross : float
        CEO gross-gross salary this month.
    month : int
        Zero-based model month.

    Returns
    -------
    (da_dict, updated_da_state)
        da_dict keys: hardware_depreciation, gpu_depreciation,
                      dev_amortization, total
        updated_da_state: new state with assets updated
    """
    # --- Compute new placements ---
    hw_capex = new_hires_this_month * HARDWARE_CAPEX_PER_HIRE
    dev_capitalised = rd_gross_gross + CEO_CAPITALISATION_RATE * ceo_gross_gross

    # --- Compute depreciation/amortization and age assets ---
    # State stores assets as (monthly_charge, remaining_months) tuples.
    # Each month we sum the charges and decrement remaining months.
    state_out: dict = {
        "hardware_assets": [],
        "gpu_assets": [],
        "dev_assets": [],
    }

    # Rebuild from input state and add new placements
    hw_assets = list(da_state.get("hardware_assets", []))
    if hw_capex > 0:
        hw_assets.append((hw_capex / HARDWARE_USEFUL_LIFE, HARDWARE_USEFUL_LIFE))

    gpu_assets = list(da_state.get("gpu_assets", []))
    if gpu_capex_this_month > 0:
        gpu_assets.append((gpu_capex_this_month / GPU_USEFUL_LIFE, GPU_USEFUL_LIFE))

    dev_assets = list(da_state.get("dev_assets", []))
    if dev_capitalised > 0:
        dev_assets.append((dev_capitalised / DEV_COST_USEFUL_LIFE, DEV_COST_USEFUL_LIFE))

    # Compute charges and age each asset category
    hardware_dep = 0.0
    for monthly_charge, months_left in hw_assets:
        if months_left > 0:
            hardware_dep += monthly_charge
            if months_left - 1 > 0:
                state_out["hardware_assets"].append((monthly_charge, months_left - 1))

    gpu_dep = 0.0
    for monthly_charge, months_left in gpu_assets:
        if months_left > 0:
            gpu_dep += monthly_charge
            if months_left - 1 > 0:
                state_out["gpu_assets"].append((monthly_charge, months_left - 1))

    dev_amort = 0.0
    for monthly_charge, months_left in dev_assets:
        if months_left > 0:
            dev_amort += monthly_charge
            if months_left - 1 > 0:
                state_out["dev_assets"].append((monthly_charge, months_left - 1))

    total_da = hardware_dep + gpu_dep + dev_amort

    da_dict = {
        "hardware_depreciation": hardware_dep,
        "gpu_depreciation": gpu_dep,
        "dev_amortization": dev_amort,
        "total": total_da,
    }

    return da_dict, state_out


# ---------------------------------------------------------------------------
# Function 4: Tax
# ---------------------------------------------------------------------------

def compute_tax_month(cfg: ModelConfig, ebit: float) -> float:
    """Compute tax for one month.

    Uses the Innovation Box rate (9%) on positive EBIT.
    Returns 0 when EBIT is negative (loss carry-forward not modelled).

    Parameters
    ----------
    cfg : ModelConfig
        Full model configuration (uses cfg.tax).
    ebit : float
        Earnings before interest and tax for this month.

    Returns
    -------
    float
        Tax amount (>= 0).
    """
    if ebit <= 0:
        return 0.0
    rate = cfg.tax.innovation_box_rate if cfg.tax.use_innovation_box else cfg.tax.standard_rate
    return ebit * rate


# === END SECTION 5: COST FUNCTIONS ===


# =========================================================================
# SECTION 6: GROWTH FUNCTIONS
# =========================================================================

# ---------------------------------------------------------------------------
# Constants  (from engine_growth.py)
# ---------------------------------------------------------------------------

# Category -> list of Roles in that category, in order.
HIRING_CATEGORIES: Dict[str, List[Role]] = {
    "founding": [
        Role.CEO,
        Role.CTO,
        Role.ENGINE_ENGINEER,
        Role.BUSINESS_DEV,
    ],
    "core_deferred": [
        # Founding team members who start paid in 2027 (revenue-gated)
        Role.AI_ENGINEER,
        Role.SALES_1,
        Role.SUPPORT_ENGINEER,
        Role.COMMUNITY_MANAGER,
    ],
    "support": [
        Role.SUPPORT_2,
        Role.SUPPORT_3,
    ],
    "sales": [
        Role.SALES_2,
        Role.SALES_3,
        Role.SALES_4,
        Role.SALES_5,
        Role.SALES_6,
        Role.SALES_7,
        Role.SALES_8,
        Role.SALES_9,
        Role.SALES_10,
    ],
    "cs": [
        Role.CUSTOMER_SUCCESS_1,
        Role.CUSTOMER_SUCCESS_2,
    ],
    "account_mgmt": [
        Role.ACCOUNT_MANAGER_1,
        Role.ACCOUNT_MANAGER_2,
    ],
    "engineering": [
        Role.SENIOR_ENGINEER,
        Role.DEVOPS,
        Role.ENGINEER_3,
        Role.ENGINEER_4,
        Role.ENGINEER_5,
        Role.ENGINEER_6,
        Role.ENGINEER_7,
        Role.QA_ENGINEER,
    ],
    "leadership": [
        Role.PRODUCT_MANAGER,
        Role.HR_MANAGER,
        Role.COO,
    ],
    "expansion": [
        Role.VP_SALES,
        Role.VP_ENGINEERING,
        Role.CFO,
        Role.MARKETING_MANAGER,
        Role.HEAD_OF_CS,
        Role.DATA_ENGINEER,
        Role.SECURITY_ENGINEER,
        Role.TECHNICAL_WRITER,
        Role.REGIONAL_SALES_US,
        Role.REGIONAL_SALES_APAC,
        Role.LEGAL_COUNSEL,
        Role.BD_BEYOND_GAMING,
        Role.SOLUTIONS_ARCHITECT,
        Role.SOLUTIONS_ENGINEER,
        Role.COMPLIANCE_OFFICER,
        Role.PARTNER_MANAGER,
        Role.OFFICE_MANAGER,
    ],
}

# Priority order of categories (checked in this order each month).
HIRING_PRIORITY: List[str] = [
    "founding",
    "core_deferred",
    "support",
    "sales",
    "cs",
    "account_mgmt",
    "engineering",
    "leadership",
    "expansion",
]


# ---------------------------------------------------------------------------
# Internal helpers  (same as simulation.py)
# ---------------------------------------------------------------------------

def _count_active_in_category(active_roles: Set[Role], category: str) -> int:
    """Count how many roles from a category are currently active."""
    return sum(1 for r in HIRING_CATEGORIES.get(category, []) if r in active_roles)


def _total_customers(customers: Dict[UserProfile, float]) -> float:
    """Sum all active customers across tiers."""
    return sum(customers.values())


def _b2b_customers(customers: Dict[UserProfile, float]) -> float:
    """Count B2B (non-Solo) customers."""
    return sum(v for k, v in customers.items() if k != UserProfile.SOLO)


def _aa_aaa_customers(customers: Dict[UserProfile, float]) -> float:
    """Count AA + AAA + Live Service customers."""
    return sum(
        customers.get(p, 0)
        for p in [UserProfile.AA, UserProfile.AAA, UserProfile.LIVE_SERVICE]
    )


def _annual_monthly(
    annual_dict: Dict[FundingScenario, List[float]],
    scenario: FundingScenario,
    year: int,
) -> float:
    """Get monthly budget from an annual-budget-by-scenario dict."""
    budgets = annual_dict.get(scenario, [0] * 10)
    y = min(year, len(budgets) - 1)
    return budgets[y] / 12.0


# ---------------------------------------------------------------------------
# Function 1: compute_leads_month
# ---------------------------------------------------------------------------

def compute_leads_month(
    cfg: ModelConfig,
    active_named_roles: Set[Role],
    scaling_sales: int,
    scaling_account_mgrs: int,
    month: int,
) -> Dict[str, float]:
    """Compute all lead sources for one month.

    Returns dict of lead_type -> count.

    Sources:
    1. Personnel-driven leads (from active roles with generates_leads=True)
    2. Organic signups (exponential growth with content boost)
    3. Marketing-driven leads (LinkedIn ABM, YouTube/Reddit, influencer, events)
    4. Scaling sales hires and scaling account managers
    """
    mult = cfg.multipliers
    pipeline_cfg = cfg.pipeline
    mkt = cfg.marketing
    scenario = cfg.funding_scenario
    year = min(month // 12, 9)

    leads: Dict[str, float] = {}

    # --- 1. Personnel-driven leads ---
    for role in active_named_roles:
        rc = ROLE_CONFIG_MAP[role]
        if rc.generates_leads and rc.leads_per_month > 0:
            lt = rc.lead_type
            base_leads = rc.leads_per_month * mult.lead_multiplier
            leads[lt] = leads.get(lt, 0) + base_leads

    # --- 2. Organic signups (with content boost) ---
    content_spend = _annual_monthly(mkt.content_production_annual, scenario, year)
    content_boost = (content_spend / 1000.0) * mkt.content_organic_boost_per_1k
    effective_growth = mult.organic_growth_rate + content_boost
    organic = mult.organic_signups_start * ((1 + effective_growth) ** month)
    leads["organic"] = leads.get("organic", 0) + organic

    # --- 3. Marketing-spend-driven leads ---

    # Events -- B2B warm leads
    event_sched = EVENT_SCHEDULE.get(scenario, {})
    tier_map = {t.name: t for t in EVENT_TIERS}
    event_b2b_leads = 0.0
    event_solo_users = 0.0
    for tier_name, events_per_year_list in event_sched.items():
        tier = tier_map.get(tier_name)
        if tier is None:
            continue
        yr = min(year, len(events_per_year_list) - 1)
        epm = events_per_year_list[yr] / 12.0  # events per month
        event_b2b_leads += epm * tier.leads_per_event
        event_solo_users += epm * pipeline_cfg.paid_users_per_event
    leads["event_b2b"] = leads.get("event_b2b", 0) + event_b2b_leads * mult.event_lead_multiplier
    leads["event_solo"] = leads.get("event_solo", 0) + event_solo_users

    # LinkedIn ABM -- B2B SQLs
    li_spend = _annual_monthly(mkt.linkedin_abm_annual, scenario, year)
    if mkt.linkedin_abm_cost_per_lead > 0 and li_spend > 0:
        linkedin_sqls = li_spend / mkt.linkedin_abm_cost_per_lead
        leads["b2b_paid"] = leads.get("b2b_paid", 0) + linkedin_sqls

    # YouTube/Reddit -- B2C signups
    yt_spend = _annual_monthly(mkt.youtube_reddit_annual, scenario, year)
    if mkt.youtube_reddit_cpm > 0 and yt_spend > 0:
        views = (yt_spend / mkt.youtube_reddit_cpm) * 1000.0
        signups = views * mkt.youtube_reddit_view_to_signup
        paid = signups * mkt.youtube_reddit_signup_to_paid
        leads["yt_reddit_paid"] = leads.get("yt_reddit_paid", 0) + paid

    # Influencer -- B2C signups
    inf_spend = _annual_monthly(mkt.influencer_annual, scenario, year)
    if mkt.influencer_avg_campaign_cost > 0 and inf_spend > 0:
        campaigns = inf_spend / mkt.influencer_avg_campaign_cost
        views = campaigns * mkt.influencer_avg_views_per_campaign
        signups = views * mkt.influencer_view_to_signup
        paid = signups * mkt.influencer_signup_to_paid
        leads["influencer_paid"] = leads.get("influencer_paid", 0) + paid

    # --- 4. Scaling sales hires ---
    if scaling_sales > 0:
        scfg = SCALING_CONFIGS["sales"]
        leads["b2b_sales"] = leads.get("b2b_sales", 0) + (
            scaling_sales * scfg.leads_per_month * mult.lead_multiplier
        )

    # --- 5. Scaling account managers ---
    if scaling_account_mgrs > 0:
        scfg = SCALING_CONFIGS["account_mgmt"]
        leads["b2b_warm"] = leads.get("b2b_warm", 0) + (
            scaling_account_mgrs * scfg.leads_per_month * mult.lead_multiplier
        )

    return leads


# ---------------------------------------------------------------------------
# Function 2: compute_new_customers_month
# ---------------------------------------------------------------------------

def compute_new_customers_month(
    cfg: ModelConfig,
    leads: Dict[str, float],
    active_customers: Dict[UserProfile, float],
    month: int,
) -> Dict[UserProfile, float]:
    """Convert leads to new customers with maturation and market caps.

    Returns dict of UserProfile -> new customers this month.
    """
    mult = cfg.multipliers
    pipeline_cfg = cfg.pipeline

    # Conversion rates with maturation over time
    years = month / 12
    opp_rate = min(
        pipeline_cfg.opp_rate_end,
        pipeline_cfg.opp_rate_start + (
            (pipeline_cfg.opp_rate_end - pipeline_cfg.opp_rate_start)
            * min(years / pipeline_cfg.opp_rate_years_to_mature, 1.0)
        ),
    )
    close_rate = min(
        pipeline_cfg.close_rate_end,
        pipeline_cfg.close_rate_start + (
            (pipeline_cfg.close_rate_end - pipeline_cfg.close_rate_start)
            * min(years / pipeline_cfg.close_rate_years_to_mature, 1.0)
        ),
    )
    close_rate *= mult.conversion_multiplier

    # Total B2B leads (warm + outreach + sales + paid + events)
    b2b_leads = sum(
        v for k, v in leads.items()
        if k in ("b2b_warm", "b2b_outreach", "b2b_sales", "b2b_paid", "event_b2b")
    )
    # B2C leads (social + organic + paid channels)
    b2c_leads = (
        leads.get("b2c_social", 0)
        + leads.get("organic", 0)
        + leads.get("yt_reddit_paid", 0)
        + leads.get("influencer_paid", 0)
        + leads.get("event_solo", 0)
    )

    # B2B conversions split by tier
    b2b_new_total = b2b_leads * opp_rate * close_rate
    b2b_tier_split = pipeline_cfg.b2b_tier_split

    # Map StudioTier splits to UserProfile
    tier_to_profile = {
        StudioTier.INDIE: UserProfile.INDIE,
        StudioTier.AA: UserProfile.AA,
        StudioTier.AAA: UserProfile.AAA,
    }

    new_customers: Dict[UserProfile, float] = {p: 0.0 for p in UserProfile}

    for tier, fraction in b2b_tier_split.items():
        profile = tier_to_profile.get(tier)
        if profile:
            new_customers[profile] += b2b_new_total * fraction

    # B2C organic -> Solo + some Narrative Designers
    b2c_converted = b2c_leads * mult.organic_conversion_to_paid
    new_customers[UserProfile.SOLO] += b2c_converted * 0.85
    new_customers[UserProfile.NARRATIVE_DESIGNER] += b2c_converted * 0.15

    # Market saturation caps (TAM-derived)
    for profile in UserProfile:
        cap = mult.max_active_customers.get(profile, float("inf"))
        existing = active_customers.get(profile, 0)
        new_customers[profile] = min(new_customers[profile], max(0, cap - existing))

    return new_customers


# ---------------------------------------------------------------------------
# Function 3: compute_churn_month
# ---------------------------------------------------------------------------

def compute_churn_month(
    cfg: ModelConfig,
    active_customers: Dict[UserProfile, float],
    month: int,
) -> Dict[UserProfile, float]:
    """Apply churn and return remaining customers per profile.

    Returns dict of UserProfile -> customers after churn.
    """
    churn_cfg = cfg.churn
    mult = cfg.multipliers

    years = month / 12
    improvement = (1.0 - churn_cfg.annual_improvement) ** years
    result: Dict[UserProfile, float] = {}
    for profile, count in active_customers.items():
        base_rate = churn_cfg.monthly_rates.get(profile, 0.05)
        effective_rate = base_rate * mult.churn_multiplier * improvement
        effective_rate = max(0, min(effective_rate, 1.0))
        result[profile] = count * (1.0 - effective_rate)
    return result


# ---------------------------------------------------------------------------
# Function 4: check_hiring_need
# ---------------------------------------------------------------------------

def check_hiring_need(
    category: str,
    active_roles: Set[Role],
    customers: Dict[UserProfile, float],
    monthly_revenue: float,
    headcount: int,
    mult: 'ScenarioMultipliers',
    funding_arrived: bool,
    scaling_hires: Dict[str, int],
) -> bool:
    """Check if a hiring category needs more people.

    Same logic as simulation._check_need, extended with scaling_hires
    context for the founding-team guard on sales.
    """
    if category == "founding":
        # Founding team is gated only by funding arrival
        return funding_arrived

    if category == "core_deferred":
        # Deferred founding team: always needed once founders are in place
        # but must pass affordability check (not hired immediately)
        founding_active = all(
            r in active_roles for r in HIRING_CATEGORIES["founding"]
        )
        return founding_active

    total = _total_customers(customers)
    b2b = _b2b_customers(customers)
    aa_aaa = _aa_aaa_customers(customers)

    # Count staff by function (check both dedicated categories and deferred roles)
    support_roles = {Role.SUPPORT_ENGINEER, Role.SUPPORT_2, Role.SUPPORT_3}
    support_count = sum(1 for r in active_roles if r in support_roles)
    cs_count = _count_active_in_category(active_roles, "cs")
    am_count = _count_active_in_category(active_roles, "account_mgmt")
    eng_roles = {
        Role.ENGINE_ENGINEER, Role.AI_ENGINEER, Role.SENIOR_ENGINEER, Role.DEVOPS,
        Role.ENGINEER_3, Role.ENGINEER_4, Role.ENGINEER_5, Role.ENGINEER_6,
        Role.ENGINEER_7, Role.QA_ENGINEER,
    }
    eng_count = sum(1 for r in active_roles if r in eng_roles)

    if category == "support":
        # Need more support when total users reach 80% of support capacity
        return total > mult.support_capacity * max(support_count, 1) * 0.8

    if category == "sales":
        # Don't scale sales before founding team is in place
        founding_complete = all(
            r in active_roles for r in HIRING_CATEGORIES["founding"]
        )
        if not founding_complete:
            return False
        # Each additional sales rep justified by potential revenue growth.
        sales_count = _count_active_in_category(active_roles, "sales")
        # Also count core_deferred sales (SALES_1)
        if Role.SALES_1 in active_roles:
            sales_count += 1
        # Need at least 1 sales rep per EUR 500K ARR, always need if <3 total
        arr = monthly_revenue * 12
        target_sales = max(3, int(arr / 500_000) + 1)
        return sales_count < target_sales

    if category == "cs":
        # Need CS when B2B accounts reach 80% of CS capacity
        return b2b > mult.cs_capacity * max(cs_count, 1) * 0.8

    if category == "account_mgmt":
        # Need account managers when AA+AAA reach 80% of AM capacity
        return aa_aaa > mult.account_mgr_capacity * max(am_count, 1) * 0.8

    if category == "engineering":
        # Need more engineers when users reach 80% of engineering capacity
        return total > mult.engineer_capacity * max(eng_count, 1) * 0.8

    if category == "leadership":
        # Product Manager at EUR 2M ARR
        # HR at 20+ headcount
        # COO at EUR 10M ARR
        arr = monthly_revenue * 12
        next_role = get_next_hire(active_roles, category)
        if next_role is None:
            return False
        if next_role == Role.PRODUCT_MANAGER:
            return arr >= 2_000_000
        if next_role == Role.HR_MANAGER:
            return headcount >= 20
        if next_role == Role.COO:
            return arr >= 10_000_000
        return False

    if category == "expansion":
        # Expansion hires: revenue-milestone driven
        arr = monthly_revenue * 12
        return arr >= 5_000_000

    return False


# ---------------------------------------------------------------------------
# Function 5: get_next_hire
# ---------------------------------------------------------------------------

def get_next_hire(
    active_roles: Set[Role],
    category: str,
) -> 'Optional[Role]':
    """Get next unhired role in a category. Returns None if all hired."""
    for role in HIRING_CATEGORIES.get(category, []):
        if role not in active_roles:
            return role
    return None


# === END SECTION 6: GROWTH FUNCTIONS ===


# =========================================================================
# SECTION 7: MAIN ENGINE
# =========================================================================

# ---------------------------------------------------------------------------
# Cash status helper
# ---------------------------------------------------------------------------

def _cash_status(cash_balance: float, operating_cash_flow: float,
                 monthly_burn: float) -> str:
    """Classify cash position into OK / WARNING / DANGER / CRITICAL / PROFITABLE."""
    if cash_balance < 0:
        return "CRITICAL"
    if operating_cash_flow > 0:
        return "PROFITABLE"
    if monthly_burn == 0:
        return "OK"
    runway = cash_balance / abs(monthly_burn) if monthly_burn < 0 else float("inf")
    if runway >= 12:
        return "OK"
    if runway >= 6:
        return "WARNING"
    if runway >= 3:
        return "DANGER"
    return "CRITICAL"


# ---------------------------------------------------------------------------
# Director adoption rate (port from director_pipeline.py, no pandas needed)
# ---------------------------------------------------------------------------

def _director_adoption_rate(cfg: ModelConfig, active_roles: Set[Role]) -> float:
    """Compute Director adoption rate from current team composition.

    Same logic as director_pipeline._director_adoption_rate but using the
    active_roles set directly instead of personnel DataFrame.
    """
    ds = cfg.director_sales
    rate = ds.base_adoption_rate  # 0.20

    if Role.BUSINESS_DEV in active_roles:
        rate += ds.bd_active_bonus  # +0.10

    sales_roles = {
        Role.SALES_1, Role.SALES_2, Role.SALES_3, Role.SALES_4,
        Role.SALES_5, Role.SALES_6, Role.SALES_7, Role.SALES_8,
        Role.SALES_9, Role.SALES_10, Role.VP_SALES,
    }
    active_sales = sum(1 for r in active_roles if r in sales_roles)
    extra_sales = max(0, active_sales - 1)
    rate += extra_sales * ds.per_extra_sales_bonus  # +0.05 each

    return min(rate, ds.max_adoption_rate)  # cap at 0.50


# ---------------------------------------------------------------------------
# Revenue lag buffer helper
# ---------------------------------------------------------------------------

def _lag_buffer_get(buf: deque, lag: int) -> float:
    """Get revenue from *lag* months ago.  Returns 0 if buffer too short."""
    if lag == 0 and len(buf) > 0:
        return buf[-1]
    if len(buf) > lag:
        return buf[-(lag + 1)]
    return 0.0


# ---------------------------------------------------------------------------
# Scaling headcount needed (helper for hiring logic)
# ---------------------------------------------------------------------------

def _compute_scaling_needed(
    func: str,
    scfg,
    customers: Dict[UserProfile, float],
    monthly_revenue: float,
    headcount: float,
    mult,
) -> int:
    """Compute number of scaling hires needed for a function.

    Returns target headcount (not delta).
    """
    total_custs = sum(customers.values())
    b2b_custs = sum(v for k, v in customers.items() if k != UserProfile.SOLO)
    aa_aaa_custs = sum(
        customers.get(p, 0)
        for p in [UserProfile.AA, UserProfile.AAA, UserProfile.LIVE_SERVICE]
    )
    arr = monthly_revenue * 12

    if func == "sales":
        # 1 sales rep per EUR 500K ARR, minimum 0 scaling (named roles handle first)
        target = max(0, int(arr / 500_000) - 3)  # subtract named sales slots
        return max(0, target)

    if func == "support":
        capacity = mult.support_capacity
        needed = max(0, int(total_custs / capacity) - 1)  # subtract named support
        return needed

    if func == "cs":
        capacity = mult.cs_capacity
        needed = max(0, int(b2b_custs / capacity) - 1)
        return needed

    if func == "account_mgmt":
        capacity = mult.account_mgr_capacity
        needed = max(0, int(aa_aaa_custs / capacity) - 1)
        return needed

    if func == "platform_eng":
        # 1 platform engineer per 10K users beyond first 5K
        needed = max(0, int((total_custs - 5_000) / 10_000))
        return needed

    if func == "research":
        # 1 researcher per EUR 5M ARR
        needed = max(0, int(arr / 5_000_000) - 1)
        return needed

    if func == "devops":
        # 1 devops per 20K users
        needed = max(0, int(total_custs / 20_000))
        return needed

    if func == "qa":
        # 1 QA per 15K users
        needed = max(0, int(total_custs / 15_000))
        return needed

    if func == "bg_bd":
        # Need more BG BD when ARR > EUR 5M (beyond-gaming is a scale-stage play)
        # 1 additional BD per EUR 10M ARR beyond first EUR 5M
        if arr < 5_000_000:
            return 0
        return max(0, int((arr - 5_000_000) / 10_000_000) + 1)

    if func == "bg_solutions":
        # Need more solutions architects when ARR > EUR 5M
        # Scale alongside BG BD (need ~1 solutions person per BD person)
        if arr < 5_000_000:
            return 0
        return max(0, int((arr - 5_000_000) / 10_000_000) + 1)

    return 0


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def run_engine(cfg: ModelConfig, gaming_only: bool = False) -> dict:
    """Run the complete financial model month-by-month.

    Every revenue, cost, and cash figure uses real formulas.
    Hiring decisions are based on actual cash balance.

    Returns dict with monthly arrays for everything:
    - revenue (architect, director, beyond_gaming, total)
    - cogs (all categories)
    - personnel (headcount, costs)
    - opex (all categories)
    - da (depreciation, amortization)
    - tax
    - cash (balance, inflows, outflows)
    - customers (per profile)
    - hiring_events
    - team composition
    """
    N = 120
    mult = cfg.multipliers

    # -----------------------------------------------------------------------
    # Pre-compute funding schedule
    # -----------------------------------------------------------------------
    funding_months: Dict[int, float] = {}
    for fe in cfg.funding_events:
        funding_months[fe.month] = funding_months.get(fe.month, 0) + fe.amount

    first_funding_month = min(funding_months.keys()) if funding_months else None

    # -----------------------------------------------------------------------
    # Mutable state
    # -----------------------------------------------------------------------
    active_roles: Set[Role] = set()
    scaling_hires: Dict[str, int] = {f: 0 for f in SCALING_CONFIGS}
    scaling_managers: Dict[str, int] = {f: 0 for f in SCALING_CONFIGS}
    customers: Dict[UserProfile, float] = {p: 0.0 for p in UserProfile}
    tenure_sum: Dict[UserProfile, float] = {p: 0.0 for p in UserProfile}

    # Initialise with actual active users
    customers[UserProfile.SOLO] = float(cfg.actuals.active_architect_users)

    cash_balance: float = cfg.actuals.cash_at_start
    funding_arrived: bool = (cfg.funding_scenario == FundingScenario.BOOTSTRAP)
    prev_headcount: float = 0.0
    loan_balance: float = 0.0  # Populated when loan arrives
    deferred_tax: float = 0.0  # Tax deferred when cash insufficient

    # Bridge loan state
    bridge_taken: bool = False
    bridge_month: int = -1
    bridge_amount: float = 0.0
    bridge_loan_balance: float = 0.0
    revenue_total_buffer: List[float] = []

    # Director state (mutable, passed to compute_director_gaming_month)
    director_state: dict = {}

    # Beyond-gaming state (mutable, passed to compute_beyond_gaming_month)
    bg_state: dict = {}
    bg_bd_first_month: int = -1  # Track when first BG BD person was hired

    # D&A state (mutable, passed to compute_da_month)
    da_state: dict = {
        "hardware_assets": [],
        "gpu_assets": [],
        "dev_assets": [],
    }

    # Revenue lag buffers
    lag = cfg.collection_lag
    architect_rev_buf: deque = deque(maxlen=max(lag.architect_tokens + 2, 2))
    director_royalty_buf: deque = deque(maxlen=max(lag.director_royalties + 2, 2))
    director_addon_buf: deque = deque(maxlen=max(lag.director_addons_onetime + 2, 2))
    director_sla_buf: deque = deque(maxlen=max(lag.director_sla + 2, 2))
    beyond_gaming_buf: deque = deque(maxlen=max(lag.beyond_gaming + 2, 2))

    # -----------------------------------------------------------------------
    # Output arrays
    # -----------------------------------------------------------------------
    out = {
        "revenue": {
            "architect_gross": [],
            "architect_token_cost": [],
            "architect_payment_proc": [],
            "architect_net": [],
            "director_royalty": [],
            "director_addon_onetime": [],
            "director_addon_sla": [],
            "director_total": [],
            "beyond_gaming": [],
            "beyond_gaming_cogs": [],
            "total": [],
        },
        "cogs": {
            "token_costs": [],
            "payment_processing": [],
            "hosting": [],
            "director": [],
            "beyond_gaming": [],
            "fx_cost": [],
            "total": [],
        },
        "personnel": {
            "headcount": [],
            "gross_gross": [],
            "wbso_benefit": [],
            "net_cost": [],
            "rd_headcount": [],
        },
        "opex": {
            "software": [], "travel": [], "office": [],
            "insurance": [], "legal": [], "hardware": [],
            "gpu_capex": [], "gpu_cloud": [], "training": [],
            "oop": [], "accounting": [], "contingency": [],
            "sales_commission": [],
            "marketing_total": [],
            "total": [],
        },
        "da": {"hardware": [], "gpu": [], "dev_amort": [], "total": []},
        "tax": [],
        "cash": {
            "balance": [],
            "revenue_received": [],
            "total_outflows": [],
            "status": [],
        },
        "customers": {p: [] for p in UserProfile},
        "tenure": {p: [] for p in UserProfile},
        "hiring_events": [],
        "team_by_month": [],
        "scaling_by_month": [],
        "scaling_managers_by_month": [],
        "director_state_by_month": [],
        "bg_state_by_month": [],
        "loan": {
            "balance": [],
            "interest": [],
            "principal": [],
            "payment": [],
        },
        "bridge_loan": {
            "amount": 0.0,
            "month": -1,
            "balance": [],
            "interest": [],
            "principal": [],
            "payment": [],
        },
        "pnl": {
            "gross_profit": [],
            "gross_margin_pct": [],
            "ebitda": [],
            "ebitda_margin_pct": [],
            "ebit": [],
            "net_income": [],
            "cumulative_net_income": [],
        },
    }

    cumulative_net_income = 0.0

    # -----------------------------------------------------------------------
    # MONTH LOOP
    # -----------------------------------------------------------------------
    for month in range(N):

        # -------------------------------------------------------------------
        # 1. FUNDING -- check for Pre-Seed / loan injection
        # -------------------------------------------------------------------
        if month == cfg.actuals.business_loan_month:
            cash_balance += cfg.actuals.business_loan
            loan_balance = cfg.actuals.business_loan

        if month in funding_months:
            cash_balance += funding_months[month]
            funding_arrived = True

        # -------------------------------------------------------------------
        # 2. LEAD GENERATION
        # -------------------------------------------------------------------
        leads = compute_leads_month(
            cfg,
            active_roles,
            scaling_hires.get("sales", 0),
            scaling_hires.get("account_mgmt", 0),
            month,
        )

        # -------------------------------------------------------------------
        # 3. CUSTOMER ACQUISITION
        # -------------------------------------------------------------------
        new_custs = compute_new_customers_month(cfg, leads, customers, month)
        for p in UserProfile:
            customers[p] += new_custs[p]

        # -------------------------------------------------------------------
        # 4. CHURN
        # -------------------------------------------------------------------
        customers = compute_churn_month(cfg, customers, month)

        # Update tenure tracking: each active customer ages one month
        for p in UserProfile:
            tenure_sum[p] += customers[p]

        # -------------------------------------------------------------------
        # 5. REVENUE
        # -------------------------------------------------------------------
        total_active_users = sum(customers.values())

        # Compute weighted average tenure per profile
        tenure_months: Dict[UserProfile, float] = {}
        for p in UserProfile:
            if customers[p] > 0:
                tenure_months[p] = tenure_sum[p] / customers[p]
            else:
                tenure_months[p] = 0.0

        # Architect token revenue
        arch = compute_architect_revenue_month(cfg, customers, tenure_months, month)

        # Director gaming revenue
        # B2B closed deals = sum of B2B lead types * opp_rate * close_rate
        b2b_lead_types = ("b2b_warm", "b2b_outreach", "b2b_sales", "b2b_paid", "event_b2b")
        b2b_leads = sum(leads.get(lt, 0) for lt in b2b_lead_types)
        years = month / 12
        opp_rate = min(
            cfg.pipeline.opp_rate_end,
            cfg.pipeline.opp_rate_start + (
                (cfg.pipeline.opp_rate_end - cfg.pipeline.opp_rate_start)
                * min(years / cfg.pipeline.opp_rate_years_to_mature, 1.0)
            ),
        )
        close_rate = min(
            cfg.pipeline.close_rate_end,
            cfg.pipeline.close_rate_start + (
                (cfg.pipeline.close_rate_end - cfg.pipeline.close_rate_start)
                * min(years / cfg.pipeline.close_rate_years_to_mature, 1.0)
            ),
        )
        close_rate *= mult.conversion_multiplier
        total_b2b_closed = b2b_leads * opp_rate * close_rate

        adoption_rate = _director_adoption_rate(cfg, active_roles)
        director_rev, director_state = compute_director_gaming_month(
            cfg, director_state, total_b2b_closed, adoption_rate, month,
        )

        # Beyond gaming -- team-driven model
        if gaming_only:
            # Zero out all beyond-gaming fields
            bg = {"revenue": 0.0, "cogs": 0.0, "active_partners": 0,
                  "new_partners": 0}
            bg_bd_count = 0
            bg_solutions_count = 0
        else:
            # Count BG BD: named role + scaling hires
            bg_bd_count = (1 if Role.BD_BEYOND_GAMING in active_roles else 0) + scaling_hires.get("bg_bd", 0)
            # Track when the first BG BD person was hired
            if bg_bd_count > 0 and bg_bd_first_month < 0:
                bg_bd_first_month = month
            # Count solutions: named roles + scaling hires
            bg_solutions_count = (
                (1 if Role.SOLUTIONS_ARCHITECT in active_roles else 0)
                + (1 if Role.SOLUTIONS_ENGINEER in active_roles else 0)
                + scaling_hires.get("bg_solutions", 0)
            )
            bg, bg_state = compute_beyond_gaming_month(
                cfg, bg_state, bg_bd_count, bg_solutions_count, month,
                bg_bd_first_month=bg_bd_first_month,
            )

        total_revenue = arch["gross_revenue"] + director_rev["total"] + bg["revenue"]

        # COGS (consolidated)
        cogs_result = compute_cogs_month(
            cfg,
            arch["gross_revenue"],
            arch["token_cost"],
            arch["payment_processing"],
            total_active_users,
            director_rev,
            bg["cogs"],
            month,
            total_revenue,
        )

        # -------------------------------------------------------------------
        # 6. PERSONNEL COSTS
        # -------------------------------------------------------------------
        pers = compute_personnel_month(
            cfg, active_roles, scaling_hires, scaling_managers, month,
        )

        # -------------------------------------------------------------------
        # 7. OPEX
        # -------------------------------------------------------------------
        opex_result = compute_opex_month(
            cfg,
            pers["total_headcount"],
            pers["total_gross_gross"],
            pers["rd_headcount"],
            pers["sales_headcount"],
            prev_headcount,
            month,
        )

        # -------------------------------------------------------------------
        # 7b. SALES COMMISSION (on direct B2B sales-sourced revenue only)
        # -------------------------------------------------------------------
        b2b_architect_rev = sum(
            arch["per_profile_revenue"].get(p, 0.0)
            for p in (UserProfile.INDIE, UserProfile.AA,
                      UserProfile.AAA, UserProfile.LIVE_SERVICE)
        )
        b2b_director_rev = director_rev["total"]
        sales_commission = (b2b_architect_rev + b2b_director_rev) * cfg.opex.sales_commission_rate

        # -------------------------------------------------------------------
        # 8. D&A
        # -------------------------------------------------------------------
        da_result, da_state = compute_da_month(
            cfg,
            da_state,
            opex_result["new_hires"],
            opex_result["gpu_capex"],
            pers["rd_gross_gross"],
            pers["ceo_gross_gross"],
            month,
        )

        # -------------------------------------------------------------------
        # 9. TAX
        # -------------------------------------------------------------------
        ebitda = (total_revenue
                  - cogs_result["total"]
                  - pers["total_net_cost"]
                  - opex_result["opex_total"]
                  - sales_commission)
        ebit = ebitda - da_result["total"]
        tax = compute_tax_month(cfg, ebit)

        # -------------------------------------------------------------------
        # 10. CASH UPDATE (with collection lags)
        # -------------------------------------------------------------------
        # Push current-month accruals into lag buffers
        architect_rev_buf.append(arch["net_revenue"])
        director_royalty_buf.append(director_rev["royalty"])
        director_addon_buf.append(director_rev["addon_onetime"])
        director_sla_buf.append(director_rev["addon_sla"])
        beyond_gaming_buf.append(bg["revenue"] - bg["cogs"])

        # Collect with appropriate lags
        cash_in_architect = _lag_buffer_get(architect_rev_buf, lag.architect_tokens)
        cash_in_dir_royalty = _lag_buffer_get(director_royalty_buf, lag.director_royalties)
        cash_in_dir_addon = _lag_buffer_get(director_addon_buf, lag.director_addons_onetime)
        cash_in_dir_sla = _lag_buffer_get(director_sla_buf, lag.director_sla)
        cash_in_bg = _lag_buffer_get(beyond_gaming_buf, lag.beyond_gaming)

        cash_in = (cash_in_architect
                   + cash_in_dir_royalty
                   + cash_in_dir_addon
                   + cash_in_dir_sla
                   + cash_in_bg)

        cash_out_before_tax = (cogs_result["total"]
                               + pers["total_net_cost"]
                               + opex_result["opex_total"]
                               + opex_result["gpu_capex"]
                               + opex_result["marketing_total"]
                               + sales_commission)

        # Tax deferral: don't let tax payment push cash negative
        cash_before_tax = cash_balance + cash_in - cash_out_before_tax
        if cash_before_tax >= tax:
            tax_paid_this_month = tax
        else:
            tax_paid_this_month = max(0.0, cash_before_tax)
            deferred_tax += (tax - tax_paid_this_month)

        cash_out = cash_out_before_tax + tax_paid_this_month
        cash_balance += cash_in - cash_out

        # Track total revenue for bridge loan trailing-12-month calc
        revenue_total_buffer.append(total_revenue)

        # --- Bridge loan: if cash goes negative and no bridge taken yet ---
        bridge_interest_mo = 0.0
        bridge_principal_mo = 0.0
        bridge_payment_mo = 0.0
        if cash_balance < 0 and not bridge_taken:
            trailing_12m = (sum(revenue_total_buffer[-12:])
                            if len(revenue_total_buffer) >= 12
                            else sum(revenue_total_buffer))
            bridge_amount = min(abs(cash_balance) + 50_000, trailing_12m * 0.40)
            bridge_amount = max(bridge_amount, 50_000)  # minimum EUR 50K
            cash_balance += bridge_amount
            bridge_taken = True
            bridge_month = month
            bridge_loan_balance = bridge_amount
            out["bridge_loan"]["amount"] = bridge_amount
            out["bridge_loan"]["month"] = bridge_month

        # --- Bridge loan repayment (same terms as business loan: 5yr, 5%, 6mo grace) ---
        if bridge_loan_balance > 0 and bridge_month >= 0 and month >= bridge_month + 6:
            bridge_term_months = 60  # 5 years
            bridge_grace = 6
            bridge_rate = 0.05
            bridge_repay_months = bridge_term_months - bridge_grace
            bridge_interest_mo = bridge_loan_balance * (bridge_rate / 12)
            bridge_principal_mo = bridge_amount / bridge_repay_months
            bridge_principal_mo = min(bridge_principal_mo, bridge_loan_balance)
            bridge_payment_mo = bridge_principal_mo + bridge_interest_mo
            bridge_loan_balance -= bridge_principal_mo
            cash_balance -= bridge_payment_mo

        # --- Loan repayment (after main cash update) ---
        loan_interest_mo = 0.0
        loan_principal_mo = 0.0
        loan_payment_mo = 0.0
        act = cfg.actuals
        if loan_balance > 0 and month >= act.business_loan_month + act.loan_grace_months:
            repayment_months = act.loan_term_months - act.loan_grace_months
            loan_interest_mo = loan_balance * (act.loan_interest_rate / 12)
            loan_principal_mo = act.business_loan / repayment_months
            loan_principal_mo = min(loan_principal_mo, loan_balance)  # don't overshoot
            loan_payment_mo = loan_principal_mo + loan_interest_mo
            loan_balance -= loan_principal_mo
            cash_balance -= loan_payment_mo

        monthly_burn = cash_out - cash_in
        operating_cf = cash_in - cash_out
        status = _cash_status(cash_balance, operating_cf, monthly_burn)

        # -------------------------------------------------------------------
        # 11. HIRING (quarterly, based on actual cash)
        # -------------------------------------------------------------------
        if month % 3 == 0:
            # Track running payroll to prevent over-hiring in a single quarter
            running_payroll = pers["total_net_cost"]

            # Named roles
            for category in HIRING_PRIORITY:
                next_role = get_next_hire(active_roles, category)
                if next_role is None:
                    continue
                if not check_hiring_need(
                    category, active_roles, customers, total_revenue,
                    int(pers["total_headcount"]), mult,
                    funding_arrived, scaling_hires,
                ):
                    continue

                # Founding team hires at funding month
                # ALL hires (including founding) must pass affordability
                rc = ROLE_CONFIG_MAP.get(next_role)
                if rc is None:
                    continue
                hire_monthly_cost = rc.monthly_gross * (1 + cfg.employer_costs.total_rate)

                if category == "founding" and funding_arrived:
                    # Founding: 12-month contract guarantee (cost vs cash + revenue)
                    total_monthly_with_hire = (running_payroll + opex_result["opex_total"]
                                               + opex_result["marketing_total"]
                                               + hire_monthly_cost)
                    twelve_month_cost = total_monthly_with_hire * 12
                    twelve_month_revenue = total_revenue * 12
                    if cash_balance + twelve_month_revenue > twelve_month_cost:
                        active_roles.add(next_role)
                        out["hiring_events"].append((month, next_role))
                        running_payroll += hire_monthly_cost
                    continue

                # Non-founding: 12-month contract guarantee (cost vs cash + revenue)
                total_monthly_with_hire = (running_payroll
                                           + opex_result["opex_total"]
                                           + opex_result["marketing_total"]
                                           + hire_monthly_cost)
                twelve_month_cost = total_monthly_with_hire * 12
                twelve_month_revenue = total_revenue * 12
                if cash_balance + twelve_month_revenue > twelve_month_cost:
                    active_roles.add(next_role)
                    out["hiring_events"].append((month, next_role))
                    running_payroll += hire_monthly_cost

            # Scaling hires
            for func, scfg in SCALING_CONFIGS.items():
                needed = _compute_scaling_needed(
                    func, scfg, customers, total_revenue, pers["total_headcount"],
                    mult,
                )
                current = scaling_hires.get(func, 0)
                if current < needed:
                    hire_cost = scfg.monthly_gross * (1 + cfg.employer_costs.total_rate)
                    total_monthly_with_hire = (running_payroll
                                               + opex_result["opex_total"]
                                               + opex_result["marketing_total"]
                                               + hire_cost)
                    twelve_month_cost = total_monthly_with_hire * 12
                    twelve_month_revenue = total_revenue * 12
                    if cash_balance + twelve_month_revenue > twelve_month_cost:
                        scaling_hires[func] = current + 1
                        running_payroll += hire_cost

            # Manager triggers
            for func, scfg in SCALING_CONFIGS.items():
                if scfg.manager_salary <= 0:
                    continue
                func_hc = scaling_hires.get(func, 0)
                needed_mgrs = func_hc // scfg.manager_ratio
                current_mgrs = scaling_managers.get(func, 0)
                if needed_mgrs > current_mgrs:
                    mgr_cost = scfg.manager_salary * (1 + cfg.employer_costs.total_rate)
                    total_monthly_with_hire = (running_payroll
                                               + opex_result["opex_total"]
                                               + opex_result["marketing_total"]
                                               + mgr_cost)
                    twelve_month_cost = total_monthly_with_hire * 12
                    twelve_month_revenue = total_revenue * 12
                    if cash_balance + twelve_month_revenue > twelve_month_cost:
                        scaling_managers[func] = current_mgrs + 1
                        running_payroll += mgr_cost

        # -------------------------------------------------------------------
        # 12. RECORD
        # -------------------------------------------------------------------
        # Revenue
        out["revenue"]["architect_gross"].append(arch["gross_revenue"])
        out["revenue"]["architect_token_cost"].append(arch["token_cost"])
        out["revenue"]["architect_payment_proc"].append(arch["payment_processing"])
        out["revenue"]["architect_net"].append(arch["net_revenue"])
        out["revenue"]["director_royalty"].append(director_rev["royalty"])
        out["revenue"]["director_addon_onetime"].append(director_rev["addon_onetime"])
        out["revenue"]["director_addon_sla"].append(director_rev["addon_sla"])
        out["revenue"]["director_total"].append(director_rev["total"])
        out["revenue"]["beyond_gaming"].append(bg["revenue"])
        out["revenue"]["beyond_gaming_cogs"].append(bg["cogs"])
        out["revenue"]["total"].append(total_revenue)

        # COGS
        out["cogs"]["token_costs"].append(cogs_result["token_costs"])
        out["cogs"]["payment_processing"].append(cogs_result["payment_processing"])
        out["cogs"]["hosting"].append(cogs_result["hosting"])
        out["cogs"]["director"].append(cogs_result["director_cogs"])
        out["cogs"]["beyond_gaming"].append(cogs_result["beyond_gaming_cogs"])
        out["cogs"]["fx_cost"].append(cogs_result["fx_cost"])
        out["cogs"]["total"].append(cogs_result["total"])

        # Personnel
        out["personnel"]["headcount"].append(pers["total_headcount"])
        out["personnel"]["gross_gross"].append(pers["total_gross_gross"])
        out["personnel"]["wbso_benefit"].append(pers["total_wbso_benefit"])
        out["personnel"]["net_cost"].append(pers["total_net_cost"])
        out["personnel"]["rd_headcount"].append(pers["rd_headcount"])

        # OpEx
        out["opex"]["software"].append(opex_result["software"])
        out["opex"]["travel"].append(opex_result["travel"])
        out["opex"]["office"].append(opex_result["office"])
        out["opex"]["insurance"].append(opex_result["insurance"])
        out["opex"]["legal"].append(opex_result["legal"])
        out["opex"]["hardware"].append(opex_result["hardware"])
        out["opex"]["gpu_capex"].append(opex_result["gpu_capex"])
        out["opex"]["gpu_cloud"].append(opex_result["gpu_cloud"])
        out["opex"]["training"].append(opex_result["training"])
        out["opex"]["oop"].append(opex_result["oop"])
        out["opex"]["accounting"].append(opex_result["accounting"])
        out["opex"]["contingency"].append(opex_result["contingency"])
        out["opex"]["sales_commission"].append(sales_commission)
        out["opex"]["marketing_total"].append(opex_result["marketing_total"])
        out["opex"]["total"].append(opex_result["opex_total"] + sales_commission)

        # D&A
        out["da"]["hardware"].append(da_result["hardware_depreciation"])
        out["da"]["gpu"].append(da_result["gpu_depreciation"])
        out["da"]["dev_amort"].append(da_result["dev_amortization"])
        out["da"]["total"].append(da_result["total"])

        # Tax
        out["tax"].append(tax)

        # Loan
        out["loan"]["balance"].append(loan_balance)
        out["loan"]["interest"].append(loan_interest_mo)
        out["loan"]["principal"].append(loan_principal_mo)
        out["loan"]["payment"].append(loan_payment_mo)

        # Bridge loan
        out["bridge_loan"]["balance"].append(bridge_loan_balance)
        out["bridge_loan"]["interest"].append(bridge_interest_mo)
        out["bridge_loan"]["principal"].append(bridge_principal_mo)
        out["bridge_loan"]["payment"].append(bridge_payment_mo)

        # Cash
        out["cash"]["balance"].append(cash_balance)
        out["cash"]["revenue_received"].append(cash_in)
        out["cash"]["total_outflows"].append(cash_out)
        out["cash"]["status"].append(status)

        # Customers & tenure
        for p in UserProfile:
            out["customers"][p].append(customers[p])
            out["tenure"][p].append(tenure_months[p])

        # Team snapshots
        out["team_by_month"].append(frozenset(active_roles))
        out["scaling_by_month"].append(dict(scaling_hires))
        out["scaling_managers_by_month"].append(dict(scaling_managers))
        out["director_state_by_month"].append({
            "cum_studios": dict(director_state.get("cum_studios", {})),
            "cum_sla_studios": dict(director_state.get("cum_sla_studios", {})),
            "pending_games_count": len(director_state.get("pending_games", [])),
        })
        out["bg_state_by_month"].append({
            "active_partners": bg.get("active_partners", 0),
            "new_partners": bg.get("new_partners", 0),
            "pending_integrations": len(bg_state.get("pending", [])),
            "bg_bd_count": bg_bd_count,
            "bg_solutions_count": bg_solutions_count,
        })

        # P&L summary
        gross_profit = total_revenue - cogs_result["total"]
        gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
        ebitda_margin_pct = (ebitda / total_revenue * 100) if total_revenue > 0 else 0.0
        net_income = ebit - tax
        cumulative_net_income += net_income

        out["pnl"]["gross_profit"].append(gross_profit)
        out["pnl"]["gross_margin_pct"].append(gross_margin_pct)
        out["pnl"]["ebitda"].append(ebitda)
        out["pnl"]["ebitda_margin_pct"].append(ebitda_margin_pct)
        out["pnl"]["ebit"].append(ebit)
        out["pnl"]["net_income"].append(net_income)
        out["pnl"]["cumulative_net_income"].append(cumulative_net_income)

        # Update prev_headcount for next month
        prev_headcount = pers["total_headcount"]

    return out


# === END SECTION 7: MAIN ENGINE ===


# =========================================================================
# SECTION 8: BROWSER API
# =========================================================================

def run_custom(params_json: str) -> str:
    """Entry point for Pyodide. Takes JSON params, returns JSON results."""
    params = json.loads(params_json)

    funding = FundingScenario(params.get('funding_scenario', 'Pre-Seed'))
    variant = UsageVariant(params.get('usage_variant', 'Low'))

    cfg = ModelConfig(funding_scenario=funding, usage_variant=variant)

    # Apply overrides
    overrides = params.get('overrides', {})
    for key, value in overrides.items():
        # Walk dotted paths like "token_economics.markup_multiplier"
        parts = key.split('.')
        obj = cfg
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)

    r = run_engine(cfg, gaming_only=params.get('gaming_only', False))
    return json.dumps(_build_results(cfg, r, params.get('gaming_only', False)))


def _build_results(cfg, r, gaming_only):
    """Convert engine output to dashboard JSON format."""
    def annual_sum(arr):
        return [sum(arr[y*12:(y+1)*12]) for y in range(10)]
    def annual_end(arr):
        return [arr[(y+1)*12-1] for y in range(10)]

    return {
        "scenario": cfg.funding_scenario.value,
        "variant": cfg.usage_variant.value,
        "gaming_only": gaming_only,
        "annual": {
            "years": list(range(1, 11)),
            "revenue": {
                "architect": annual_sum(r["revenue"]["architect_gross"]),
                "director_royalty": annual_sum(r["revenue"]["director_royalty"]),
                "director_addons": [sum(r["revenue"]["director_addon_onetime"][y*12:(y+1)*12]) + sum(r["revenue"]["director_addon_sla"][y*12:(y+1)*12]) for y in range(10)],
                "beyond_gaming": annual_sum(r["revenue"]["beyond_gaming"]),
                "total": annual_sum(r["revenue"]["total"]),
            },
            "costs": {
                "cogs": annual_sum(r["cogs"]["total"]),
                "personnel": annual_sum(r["personnel"]["net_cost"]),
                "opex": annual_sum(r["opex"]["total"]),
            },
            "profit": {
                "ebitda": annual_sum(r["pnl"]["ebitda"]),
                "net_income": annual_sum(r["pnl"]["net_income"]),
            },
            "team": {"headcount": annual_end(r["personnel"]["headcount"])},
            "customers": {"total": [sum(r["customers"][p][(y+1)*12-1] for p in UserProfile) for y in range(10)]},
            "cash": {"balance": annual_end(r["cash"]["balance"])},
        },
        "monthly": {
            "revenue_total": r["revenue"]["total"],
            "cash_balance": r["cash"]["balance"],
            "headcount": r["personnel"]["headcount"],
            "customers_total": [sum(r["customers"][p][m] for p in UserProfile) for m in range(120)],
        },
        "summary": {
            "y5_arr": r["revenue"]["total"][59] * 12,
            "y10_arr": r["revenue"]["total"][119] * 12,
            "y5_headcount": r["personnel"]["headcount"][59],
            "y10_headcount": r["personnel"]["headcount"][119],
            "min_cash": min(r["cash"]["balance"]),
            "breakeven_month": next((m for m in range(120) if r["pnl"]["ebitda"][m] > 0), -1),
            "bg_start_month": next((m for m in range(120) if r["revenue"]["beyond_gaming"][m] > 0), -1),
        },
    }


# === END SECTION 8: BROWSER API ===


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_custom('{"funding_scenario": "Pre-Seed", "usage_variant": "Low"}')
    data = json.loads(result)
    print(f"Y5 ARR: EUR {data['summary']['y5_arr']:,.0f}")
    print(f"Y10 ARR: EUR {data['summary']['y10_arr']:,.0f}")
