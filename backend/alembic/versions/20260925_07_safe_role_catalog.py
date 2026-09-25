"""Reframe existing AI employees as supervised support roles."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_07"
down_revision = "20260925_06"
branch_labels = None
depends_on = None

SAFE_ROLES = {
    "executive-assistant": ("Administrative Coordination Assistant", ["Briefings", "Scheduling drafts", "Task tracking"]),
    "operations-manager": ("Operations Coordination Assistant", ["Process analysis", "Status reporting", "Workflow coordination"]),
    "financial-analyst": ("Financial Reporting Assistant", ["Variance analysis", "Reconciliation support", "Report drafting"]),
    "people-operations-partner": ("HR Policy & Onboarding Assistant", ["Policy retrieval", "Onboarding support", "Document checklists"]),
    "sales-development": ("Sales Research & Drafting Assistant", ["Prospect research", "Outreach drafts", "CRM data preparation"]),
    "marketing-specialist": ("Marketing Content Assistant", ["Content drafting", "Campaign research", "Performance summaries"]),
    "customer-support-specialist": ("Customer Support Drafting Assistant", ["Knowledge retrieval", "Case triage", "Response drafts"]),
    "product-manager": ("Product Research Assistant", ["Research synthesis", "Requirement drafts", "Delivery summaries"]),
    "software-engineer": ("Software Development Assistant", ["Code suggestions", "Test generation", "Documentation"]),
    "it-support-specialist": ("IT Helpdesk Triage Assistant", ["Troubleshooting guidance", "Ticket triage", "Documentation"]),
    "data-analyst": ("Data Analysis Assistant", ["Data analysis", "Visualisation drafts", "Report drafting"]),
    "security-analyst": ("Security Alert Triage Assistant", ["Alert summarisation", "Evidence collation", "Incident-report drafts"]),
    "compliance-analyst": ("Compliance Review Assistant", ["Policy comparison", "Evidence organisation", "Audit preparation"]),
    "procurement-analyst": ("Procurement Research Assistant", ["Supplier research", "Comparison drafts", "Spend analysis"]),
    "strategy-analyst": ("Strategy Research Assistant", ["Research synthesis", "Scenario drafts", "Executive briefings"]),
}

OLD_ROLES = {
    "executive-assistant": ("Executive Assistant", ["Briefings", "Scheduling", "Task tracking"]),
    "operations-manager": ("Operations Manager", ["Process analysis", "Planning", "Reporting"]),
    "financial-analyst": ("Financial Analyst", ["Financial analysis", "Forecasting", "Reporting"]),
    "people-operations-partner": ("People Operations Partner", ["Policy guidance", "Onboarding", "Employee support"]),
    "sales-development": ("Sales Development Representative", ["Prospect research", "Outreach drafts", "CRM updates"]),
    "marketing-specialist": ("Marketing Specialist", ["Content drafting", "Campaign planning", "Analytics"]),
    "customer-support-specialist": ("Customer Support Specialist", ["Knowledge retrieval", "Case triage", "Response drafts"]),
    "product-manager": ("Product Manager", ["Research synthesis", "Requirements", "Roadmaps"]),
    "software-engineer": ("Software Engineer", ["Coding", "Code review", "Testing"]),
    "it-support-specialist": ("IT Support Specialist", ["Troubleshooting", "Ticket triage", "Documentation"]),
    "data-analyst": ("Data Analyst", ["Data analysis", "Visualisation", "Reporting"]),
    "security-analyst": ("Security Analyst", ["Risk review", "Alert triage", "Incident reporting"]),
    "compliance-analyst": ("Compliance Analyst", ["Policy checks", "Evidence review", "Audit support"]),
    "procurement-analyst": ("Procurement Analyst", ["Supplier research", "Comparison", "Spend analysis"]),
    "strategy-analyst": ("Strategy Analyst", ["Research", "Scenario analysis", "Executive briefs"]),
}

assistants = sa.table("assistants", sa.column("role_template_id", sa.String), sa.column("role", sa.String), sa.column("capabilities", sa.JSON))


def apply_roles(roles: dict[str, tuple[str, list[str]]]) -> None:
    for role_id, (name, capabilities) in roles.items():
        op.execute(assistants.update().where(assistants.c.role_template_id == role_id).values(role=name, capabilities=capabilities))


def upgrade() -> None:
    apply_roles(SAFE_ROLES)


def downgrade() -> None:
    apply_roles(OLD_ROLES)
