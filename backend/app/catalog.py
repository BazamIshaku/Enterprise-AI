"""Curated departments and starter roles for governed AI employees."""

DEPARTMENTS = [
    {"id": "leadership", "name": "Leadership & Strategy"},
    {"id": "operations", "name": "Operations"},
    {"id": "finance", "name": "Finance & Accounting"},
    {"id": "people", "name": "People & Human Resources"},
    {"id": "sales", "name": "Sales"},
    {"id": "marketing", "name": "Marketing & Communications"},
    {"id": "customer-success", "name": "Customer Success & Support"},
    {"id": "product", "name": "Product Management"},
    {"id": "engineering", "name": "Engineering & IT"},
    {"id": "data", "name": "Data & Analytics"},
    {"id": "security", "name": "Security & Risk"},
    {"id": "legal", "name": "Legal & Compliance"},
    {"id": "procurement", "name": "Procurement & Supply Chain"},
    {"id": "administration", "name": "Administration"},
]

ROLE_TEMPLATES = [
    {"id": "executive-assistant", "department_id": "administration", "name": "Executive Assistant", "description": "Coordinates briefs, meetings, follow-ups, and approved communications.", "capabilities": ["Briefings", "Scheduling", "Task tracking"]},
    {"id": "operations-manager", "department_id": "operations", "name": "Operations Manager", "description": "Monitors processes, identifies blockers, and prepares operating updates.", "capabilities": ["Process analysis", "Planning", "Reporting"]},
    {"id": "financial-analyst", "department_id": "finance", "name": "Financial Analyst", "description": "Prepares controlled financial analysis and management summaries.", "capabilities": ["Financial analysis", "Forecasting", "Reporting"]},
    {"id": "people-operations-partner", "department_id": "people", "name": "People Operations Partner", "description": "Supports documented people processes while escalating sensitive decisions.", "capabilities": ["Policy guidance", "Onboarding", "Employee support"]},
    {"id": "sales-development", "department_id": "sales", "name": "Sales Development Representative", "description": "Researches prospects and drafts approved outreach and follow-ups.", "capabilities": ["Prospect research", "Outreach drafts", "CRM updates"]},
    {"id": "marketing-specialist", "department_id": "marketing", "name": "Marketing Specialist", "description": "Creates on-brand campaign drafts and performance summaries.", "capabilities": ["Content drafting", "Campaign planning", "Analytics"]},
    {"id": "customer-support-specialist", "department_id": "customer-success", "name": "Customer Support Specialist", "description": "Answers questions from approved sources and escalates uncertain cases.", "capabilities": ["Knowledge retrieval", "Case triage", "Response drafts"]},
    {"id": "product-manager", "department_id": "product", "name": "Product Manager", "description": "Synthesises research, requirements, priorities, and delivery updates.", "capabilities": ["Research synthesis", "Requirements", "Roadmaps"]},
    {"id": "software-engineer", "department_id": "engineering", "name": "Software Engineer", "description": "Assists with scoped implementation, review, testing, and documentation.", "capabilities": ["Coding", "Code review", "Testing"]},
    {"id": "it-support-specialist", "department_id": "engineering", "name": "IT Support Specialist", "description": "Troubleshoots documented issues and escalates privileged actions.", "capabilities": ["Troubleshooting", "Ticket triage", "Documentation"]},
    {"id": "data-analyst", "department_id": "data", "name": "Data Analyst", "description": "Analyses approved datasets and produces traceable insights.", "capabilities": ["Data analysis", "Visualisation", "Reporting"]},
    {"id": "security-analyst", "department_id": "security", "name": "Security Analyst", "description": "Reviews security signals and prepares evidence-based escalations.", "capabilities": ["Risk review", "Alert triage", "Incident reporting"]},
    {"id": "compliance-analyst", "department_id": "legal", "name": "Compliance Analyst", "description": "Checks work against approved policies without replacing legal judgment.", "capabilities": ["Policy checks", "Evidence review", "Audit support"]},
    {"id": "procurement-analyst", "department_id": "procurement", "name": "Procurement Analyst", "description": "Compares suppliers and prepares controlled purchasing analysis.", "capabilities": ["Supplier research", "Comparison", "Spend analysis"]},
    {"id": "strategy-analyst", "department_id": "leadership", "name": "Strategy Analyst", "description": "Synthesises approved evidence into options for leadership review.", "capabilities": ["Research", "Scenario analysis", "Executive briefs"]},
]

DEPARTMENT_BY_ID = {item["id"]: item for item in DEPARTMENTS}
ROLE_BY_ID = {item["id"]: item for item in ROLE_TEMPLATES}
