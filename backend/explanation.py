"""Evidence-only template explanation for P0."""

from __future__ import annotations

from .schemas import Intent, Outfit


def build_explanation(outfit: Outfit, intent: Intent) -> str:
    facts: list[str] = []
    if intent.preferred.styles and any(set(intent.preferred.styles) & set(item.styles) for item in outfit.items):
        facts.append("符合偏好的風格")
    if intent.preferred.fits and any(item.fit in intent.preferred.fits for item in outfit.items):
        facts.append("包含偏好的版型")
    if intent.budget_total is not None and outfit.total_price <= intent.budget_total:
        facts.append(f"整套 NT${outfit.total_price}，在 NT${intent.budget_total} 預算內")
    if not facts:
        facts.append("包含所需的上衣、下身與鞋子")
    return "；".join(facts) + "。"
