"""AskData Skills — pre-built industry metric templates.

Each skill is a self-contained directory with:
  - metrics.yaml   the canonical metric definitions + SQL templates
  - README.md      the human-readable description

Available skills (drop more under askdata_skills/):
  - ecommerce   12 metrics for online retail
  - saas        9 metrics for subscription SaaS
  - education   8 metrics for online / offline education
"""
__all__ = ["SKILLS_AVAILABLE"]

SKILLS_AVAILABLE = ("ecommerce", "saas", "education")
