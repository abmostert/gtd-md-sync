from __future__ import annotations

import shutil
import textwrap


def _print_wrapped(text: str, *, indent: str = "", width: int = 80) -> None:
    available = max(20, width - len(indent))

    wrapped = textwrap.wrap(
        text,
        width=available,
        break_long_words=False,
        break_on_hyphens=False,
    )

    if not wrapped:
        print()
        return

    for line in wrapped:
        print(f"{indent}{line}")


def cmd_workflow() -> int:
    width = shutil.get_terminal_size(fallback=(80, 24)).columns

    # Keep very wide terminals readable.
    width = min(width, 100)

    print()
    print("GTD WORKFLOW")
    print("=" * min(width, 40))
    print()

    print("1. CAPTURE")
    _print_wrapped(
        "Get everything that has your attention out of your head and into a trusted inbox.",
        indent="   ",
        width=width,
    )
    print()

    print("2. CLARIFY")
    print("   Is it actionable?")
    print()
    print("   NO")
    print("     ├─ Trash")
    print("     ├─ Someday / Maybe")
    print("     └─ Reference")
    print()
    print("   YES")
    print("     ├─ Can it be done in one action?")
    print("     │    ├─ Yes → Next Action / Waiting For / Calendar")
    print("     │    └─ No  → Project")
    print("     │              ├─ Define the desired outcome")
    print("     │              └─ Define the next action")
    print("     └─ If it takes less than 2 minutes → consider doing it now")
    print()

    print("3. ORGANIZE")
    print("   Put clarified items where they belong:")
    print()
    print("     • Next Actions")
    print("     • Projects")
    print("     • Waiting For")
    print("     • Calendar")
    print("     • Someday / Maybe")
    print("     • Reference")
    print()

    print("4. REVIEW")
    _print_wrapped(
        "Keep the system current and trusted. Review projects, next actions, "
        "waiting items, Someday / Maybe, and supporting material regularly.",
        indent="   ",
        width=width,
    )
    print()

    print("5. ENGAGE")
    _print_wrapped(
        "Choose what to do from the trusted system based on context, available "
        "time, priority, and capacity.",
        indent="   ",
        width=width,
    )
    print()

    print("QUICK DECISION PATH")
    print("   Capture → Clarify → Organize → Review → Engage")
    print()

    return 0