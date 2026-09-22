"""CLI: list all available AskData skills."""
import sys

# Force UTF-8 stdout so emoji render on Windows CMD / PowerShell.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from askdata.skills.registry import SkillRegistry  # noqa: E402


def main():
    reg = SkillRegistry()
    skills = reg.list_skills()
    if not skills:
        print("[!] No skills found under askdata_skills/")
        return
    print(f"\n[Skills] Found {len(skills)} skill(s):\n")
    for s in skills:
        print(reg.describe(s["name"]))
        print()


if __name__ == "__main__":
    main()

