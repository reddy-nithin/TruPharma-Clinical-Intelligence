"""
Opioid Watchdog Agent
=====================
Standalone agent module that provides structured opioid intelligence
queries across pharmacology, safety signals, NLP label insights, and
epidemiological context.

Can be imported into the main TruPharma app:
    from opioid_track.agents.opioid_watchdog import OpioidWatchdog

Or used independently within the opioid dashboard.
"""

import json
import os
from typing import Optional

from opioid_track import config
from opioid_track.core.registry import (
    calculate_daily_mme,
    get_drugs_containing_ingredient,
    get_mme_factor,
    get_opioid_profile,
    is_opioid,
    search_opioid_products,
)


class OpioidWatchdog:
    """Opioid intelligence agent providing structured queries across all Tier 1–3 data."""

    def __init__(
        self,
        registry: Optional[dict] = None,
        pharmacology_data: Optional[dict] = None,
        signal_data: Optional[list] = None,
        nlp_insights: Optional[dict] = None,
    ):
        self.registry = registry or self._load_json(config.REGISTRY_OUTPUT)
        self.pharmacology = pharmacology_data or self._load_json(config.PHARMACOLOGY_OUTPUT)
        self.signals = signal_data if signal_data is not None else self._load_signals()
        self.nlp = nlp_insights or self._load_json(config.NLP_INSIGHTS_OUTPUT)

        self._ingredient_pharm = self.pharmacology.get("ingredient_pharmacology", {})
        self._drug_insights = self.nlp.get("drug_label_insights", [])
        self._comparison_matrix = self.nlp.get("comparison_matrix", [])
        self._drugs_list = self.registry.get("opioid_drugs", [])

    @staticmethod
    def _load_json(path: str) -> dict:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def _load_signals(self) -> list:
        data = self._load_json(config.SIGNAL_RESULTS_OUTPUT)
        return data.get("signals", [])

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def _find_drug(self, name_or_rxcui: str) -> Optional[dict]:
        """Find a drug in the registry by name or RxCUI."""
        q = name_or_rxcui.strip()
        for drug in self._drugs_list:
            if drug["rxcui"] == q:
                return drug
            if q.lower() in drug["drug_name"].lower():
                return drug
            for ing in drug.get("active_ingredients", []):
                if ing.get("rxcui") == q or q.lower() == ing.get("name", "").lower():
                    return drug
        return None

    def _find_ingredient_name(self, name_or_rxcui: str) -> Optional[str]:
        """Resolve a drug name/rxcui to an ingredient name in pharmacology data."""
        q = name_or_rxcui.strip().lower()
        if q in self._ingredient_pharm:
            return q

        for ing_name, data in self._ingredient_pharm.items():
            if data.get("rxcui_ingredient") == name_or_rxcui.strip():
                return ing_name

        drug = self._find_drug(name_or_rxcui)
        if drug:
            for ing in drug.get("active_ingredients", []):
                if ing.get("is_opioid_component"):
                    n = ing["name"].lower()
                    if n in self._ingredient_pharm:
                        return n
            name_parts = drug["drug_name"].lower().split()
            for ing_name in self._ingredient_pharm:
                if ing_name in name_parts:
                    return ing_name
        return None

    def _find_nlp_entry(self, name_or_rxcui: str) -> Optional[dict]:
        """Find an NLP label insight entry."""
        q = name_or_rxcui.strip()
        for entry in self._drug_insights:
            if entry.get("rxcui") == q:
                return entry
            if q.lower() in entry.get("drug_name", "").lower():
                return entry
        return None

    def _get_drug_signals(self, drug_name: str) -> list[dict]:
        """Get all FAERS signals for a drug."""
        q = drug_name.strip().lower()
        return [s for s in self.signals if s.get("drug_name", "").lower() == q]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_opioid_query(self, drug_name_or_rxcui: str) -> bool:
        """Check if a drug/ingredient itself is a known opioid.

        Returns True only if the queried substance is an opioid component,
        not merely present in a combination product (e.g., aspirin in
        aspirin/codeine would return False).
        """
        q = drug_name_or_rxcui.strip()
        q_lower = q.lower()

        if q_lower in self._ingredient_pharm:
            return True

        for ing_name, data in self._ingredient_pharm.items():
            if data.get("rxcui_ingredient") == q:
                return True

        for drug in self._drugs_list:
            if drug["rxcui"] == q:
                return True
            for ing in drug.get("active_ingredients", []):
                if ing.get("is_opioid_component") and q_lower == ing.get("name", "").lower():
                    return True

        return False

    def get_full_opioid_brief(self, rxcui: str) -> dict:
        """Return a comprehensive opioid intelligence brief for a given RxCUI.

        Returns dict with: identity, pharmacology, safety, signals,
        label_highlights, prescribing_context, epidemic_context.
        """
        drug = self._find_drug(rxcui)
        if not drug:
            return {"error": f"No opioid found for RxCUI {rxcui}"}

        ing_name = self._find_ingredient_name(rxcui)
        pharm = self._ingredient_pharm.get(ing_name, {}) if ing_name else {}
        nlp_entry = self._find_nlp_entry(rxcui)

        identity = {
            "drug_name": drug["drug_name"],
            "rxcui": drug["rxcui"],
            "schedule": drug.get("schedule", ""),
            "opioid_category": drug.get("opioid_category", ""),
            "active_ingredients": [
                {
                    "name": i.get("name"),
                    "is_opioid_component": i.get("is_opioid_component", False),
                }
                for i in drug.get("active_ingredients", [])
            ],
        }

        pharmacology_summary = {}
        if pharm:
            affinities = pharm.get("receptor_affinities", {})
            pharmacology_summary = {
                "ingredient": ing_name,
                "receptor_affinities": {
                    r: {"ki_nM": d.get("ki_nM"), "source": d.get("source")}
                    for r, d in affinities.items()
                },
                "potency_vs_morphine": pharm.get("potency_vs_morphine"),
                "why_its_an_opioid": pharm.get("why_its_an_opioid", ""),
                "half_life_hours": pharm.get("half_life_hours"),
                "metabolism": pharm.get("metabolism", ""),
                "active_metabolites": pharm.get("active_metabolites", []),
            }

        safety_summary = {}
        if pharm:
            safety_summary = {
                "danger_level": pharm.get("danger_level", "Unknown"),
                "danger_rank": pharm.get("danger_rank"),
                "estimated_human_lethal_dose_mg": pharm.get("estimated_human_lethal_dose_mg"),
                "therapeutic_index": pharm.get("therapeutic_index"),
                "ld50_data": pharm.get("ld50_data", []),
            }

        mme_factor = get_mme_factor(ing_name) if ing_name else None
        if mme_factor:
            safety_summary["mme_conversion_factor"] = mme_factor

        drug_signals = self._get_drug_signals(ing_name) if ing_name else []
        consensus = [s for s in drug_signals if s.get("consensus_signal")]
        signals_summary = {
            "total_signals": len(drug_signals),
            "consensus_signals": len(consensus),
            "top_signals": [
                {
                    "reaction": s["reaction"],
                    "report_count": s["report_count"],
                    "methods_flagging": s["methods_flagging"],
                }
                for s in sorted(consensus, key=lambda x: x["report_count"], reverse=True)[:5]
            ],
        }

        label_highlights = {}
        if nlp_entry:
            bw = nlp_entry.get("boxed_warning", {})
            label_highlights = {
                "has_boxed_warning": bw.get("present", False),
                "boxed_warning_count": bw.get("paragraph_count", 0),
                "key_warnings": bw.get("key_warnings", []),
                "rems_required": nlp_entry.get("rems", {}).get("rems_required", False),
                "rems_type": nlp_entry.get("rems", {}).get("rems_type"),
                "drug_interactions_benzo": nlp_entry.get("drug_interactions", {}).get("benzo_warning", False),
                "cyp_interactions": nlp_entry.get("drug_interactions", {}).get("cyp_interactions", []),
                "max_daily_dose_mg": nlp_entry.get("dosage", {}).get("max_daily_dose_mg"),
                "overdose_symptoms": nlp_entry.get("overdosage", {}).get("symptoms", []),
                "naloxone_rescue_dose": nlp_entry.get("overdosage", {}).get("naloxone_rescue_dose"),
            }

        prescribing_ctx = {}
        if mme_factor:
            prescribing_ctx["mme_factor"] = mme_factor
            prescribing_ctx["mme_guidance"] = (
                "CDC recommends avoiding doses >= 90 MME/day or carefully "
                "justifying the decision to titrate above 50 MME/day."
            )

        return {
            "identity": identity,
            "pharmacology": pharmacology_summary,
            "safety": safety_summary,
            "signals": signals_summary,
            "label_highlights": label_highlights,
            "prescribing_context": prescribing_ctx,
        }

    def answer_why_opioid(self, drug_name: str) -> str:
        """Explain why a substance is classified as an opioid, citing receptor data."""
        ing = self._find_ingredient_name(drug_name)
        if not ing:
            return (
                f"'{drug_name}' was not found in the opioid pharmacology database. "
                "It may not be an opioid, or data has not been fetched for it."
            )

        pharm = self._ingredient_pharm[ing]
        explanation = pharm.get("why_its_an_opioid", "")
        if explanation:
            return explanation

        affinities = pharm.get("receptor_affinities", {})
        if "mu" in affinities:
            ki = affinities["mu"].get("ki_nM")
            return (
                f"{ing.title()} binds the mu opioid receptor (OPRM1) with "
                f"Ki = {ki} nM, qualifying it as an opioid receptor ligand."
            )
        return f"{ing.title()} is listed in the opioid registry but detailed receptor data is not available."

    def compare_danger(self, drug1: str, drug2: str) -> str:
        """Compare the danger profiles of two opioids with specific numbers."""
        ing1 = self._find_ingredient_name(drug1)
        ing2 = self._find_ingredient_name(drug2)

        if not ing1:
            return f"'{drug1}' not found in pharmacology data."
        if not ing2:
            return f"'{drug2}' not found in pharmacology data."

        p1 = self._ingredient_pharm[ing1]
        p2 = self._ingredient_pharm[ing2]

        lines = [f"## Danger Comparison: {ing1.title()} vs {ing2.title()}\n"]

        for label, p, name in [("1", p1, ing1), ("2", p2, ing2)]:
            d_level = p.get("danger_level", "Unknown")
            leth = p.get("estimated_human_lethal_dose_mg")
            ti = p.get("therapeutic_index")
            potency = p.get("potency_vs_morphine")
            mu_ki = p.get("receptor_affinities", {}).get("mu", {}).get("ki_nM")

            lines.append(f"**{name.title()}:**")
            lines.append(f"  - Danger level: {d_level}")
            if leth is not None:
                lines.append(f"  - Estimated human lethal dose: {leth:.1f} mg")
            else:
                lines.append("  - Estimated human lethal dose: not available")
            if ti is not None:
                lines.append(f"  - Therapeutic index: {ti:.1f}")
            if potency is not None:
                lines.append(f"  - Potency vs morphine: {potency:.2f}x")
            if mu_ki is not None:
                lines.append(f"  - Mu receptor Ki: {mu_ki} nM")
            lines.append("")

        potency1 = p1.get("potency_vs_morphine") or 0
        potency2 = p2.get("potency_vs_morphine") or 0
        if potency1 and potency2:
            if potency1 > potency2:
                ratio = potency1 / potency2
                lines.append(
                    f"**Conclusion:** {ing1.title()} is approximately {ratio:.1f}x "
                    f"more potent than {ing2.title()} at the mu opioid receptor."
                )
            elif potency2 > potency1:
                ratio = potency2 / potency1
                lines.append(
                    f"**Conclusion:** {ing2.title()} is approximately {ratio:.1f}x "
                    f"more potent than {ing1.title()} at the mu opioid receptor."
                )
            else:
                lines.append(f"**Conclusion:** Both drugs have similar potency at the mu receptor.")

        return "\n".join(lines)

    def get_signals_summary(self, rxcui: str) -> str:
        """Summarize FAERS pharmacovigilance signals for a drug."""
        ing = self._find_ingredient_name(rxcui)
        if not ing:
            drug = self._find_drug(rxcui)
            label = drug["drug_name"] if drug else rxcui
            return f"No pharmacology data for '{label}'; cannot match to FAERS signals."

        sigs = self._get_drug_signals(ing)
        if not sigs:
            return f"No FAERS signals detected for {ing.title()}. Signal detection may not have been run for this drug."

        consensus = [s for s in sigs if s.get("consensus_signal")]
        partial = [s for s in sigs if not s.get("consensus_signal")]

        lines = [f"## FAERS Signal Summary for {ing.title()}\n"]
        lines.append(f"Total signal pairs analyzed: {len(sigs)}")
        lines.append(f"Consensus signals (≥2 methods): {len(consensus)}")
        lines.append(f"Partial signals (1 method only): {len(partial)}\n")

        if consensus:
            lines.append("### Consensus Signals (strongest evidence):")
            for s in sorted(consensus, key=lambda x: x["report_count"], reverse=True)[:10]:
                prr_val = s.get("prr", {}).get("value")
                ror_val = s.get("ror", {}).get("value")
                ebgm_val = s.get("mgps", {}).get("ebgm")
                lines.append(
                    f"  - **{s['reaction']}**: {s['report_count']} reports, "
                    f"{s['methods_flagging']}/3 methods flagging"
                )
                metrics = []
                if prr_val:
                    metrics.append(f"PRR={prr_val:.2f}")
                if ror_val:
                    metrics.append(f"ROR={ror_val:.2f}")
                if ebgm_val:
                    metrics.append(f"EBGM={ebgm_val:.2f}")
                if metrics:
                    lines.append(f"    ({', '.join(metrics)})")

        return "\n".join(lines)

    def get_label_warnings(self, rxcui: str) -> str:
        """Summarize NLP-mined label warnings for a drug."""
        nlp_entry = self._find_nlp_entry(rxcui)
        if not nlp_entry:
            for entry in self._drug_insights:
                drug = self._find_drug(rxcui)
                if drug:
                    for ing in drug.get("active_ingredients", []):
                        if ing.get("name", "").lower() in entry.get("drug_name", "").lower():
                            nlp_entry = entry
                            break
                if nlp_entry:
                    break

        if not nlp_entry:
            return f"No NLP label data available for RxCUI {rxcui}."

        lines = [f"## Label Warnings: {nlp_entry['drug_name']}\n"]

        bw = nlp_entry.get("boxed_warning", {})
        if bw.get("present"):
            lines.append("### BOXED WARNING (Black Box)")
            warnings = bw.get("key_warnings", [])
            if warnings:
                lines.append(f"Key warnings: {', '.join(warnings)}")
            text = bw.get("full_text", "")
            if text:
                preview = text[:500] + ("..." if len(text) > 500 else "")
                lines.append(f"\n{preview}\n")
        else:
            lines.append("No boxed warning on this label.\n")

        rems = nlp_entry.get("rems", {})
        if rems.get("rems_required"):
            lines.append(f"**REMS Required:** Yes — {rems.get('rems_type', 'type not specified')}")
        else:
            lines.append("**REMS Required:** No")

        dosage = nlp_entry.get("dosage", {})
        if dosage.get("starting_dose"):
            lines.append(f"**Starting dose:** {dosage['starting_dose']}")
        if dosage.get("max_daily_dose_mg"):
            lines.append(f"**Max daily dose:** {dosage['max_daily_dose_mg']} mg")

        di = nlp_entry.get("drug_interactions", {})
        if di.get("benzo_warning"):
            lines.append("**Benzodiazepine interaction warning:** YES")
        cyp = di.get("cyp_interactions", [])
        if cyp:
            lines.append(f"**CYP enzyme interactions:** {', '.join(cyp)}")

        od = nlp_entry.get("overdosage", {})
        symptoms = od.get("symptoms", [])
        if symptoms:
            lines.append(f"**Overdose symptoms:** {', '.join(symptoms)}")
        nalox = od.get("naloxone_rescue_dose")
        if nalox:
            lines.append(f"**Naloxone rescue dose:** {nalox}")

        return "\n".join(lines)

    def find_drugs_with_ingredient(self, ingredient: str) -> list[dict]:
        """Find all products containing a specific opioid ingredient."""
        ing_lower = ingredient.strip().lower()

        ing_pharm = self._ingredient_pharm.get(ing_lower, {})
        if ing_pharm and ing_pharm.get("products_containing"):
            return ing_pharm["products_containing"]

        results = []
        for drug in self._drugs_list:
            for ing in drug.get("active_ingredients", []):
                if ing_lower in ing.get("name", "").lower():
                    results.append({
                        "rxcui": drug["rxcui"],
                        "drug_name": drug["drug_name"],
                        "schedule": drug.get("schedule", ""),
                        "tty": drug.get("tty", ""),
                    })
                    break
        return results

    def rank_ingredient_sensitivity(self, drug_name_or_rxcui: str) -> dict:
        """Rank all active ingredients in a drug by sensitivity/danger.

        Returns dict with: drug_name, ingredients (sorted most→least sensitive),
        most_sensitive_ingredient, explanation.
        """
        drug = self._find_drug(drug_name_or_rxcui)
        if not drug:
            return {"error": f"'{drug_name_or_rxcui}' not found in registry."}

        ingredients = drug.get("active_ingredients", [])
        if not ingredients:
            return {"error": f"No active ingredients found for '{drug['drug_name']}'."}

        scored = []
        for ing in ingredients:
            name = ing.get("name", "").lower()
            is_opioid = ing.get("is_opioid_component", False)
            pharm = self._ingredient_pharm.get(name, {})

            # --- Composite sensitivity score (0–100) ---
            # Higher = more dangerous / more sensitive
            score = 0.0
            factors = []

            # Factor 1: danger_rank (1=most dangerous → higher score)
            danger_rank = pharm.get("danger_rank")
            total_ranked = len(self._ingredient_pharm)
            if danger_rank is not None and total_ranked > 0:
                rank_score = max(0, (1 - (danger_rank - 1) / max(total_ranked, 1))) * 30
                score += rank_score
                factors.append(f"Danger rank #{danger_rank}/{total_ranked}")

            # Factor 2: therapeutic index (lower = more dangerous)
            ti = pharm.get("therapeutic_index")
            if ti is not None and ti > 0:
                ti_score = min(25, max(0, (1 - ti / 100) * 25))
                score += ti_score
                factors.append(f"Therapeutic index: {ti:.1f}")

            # Factor 3: potency vs morphine (higher = more dangerous)
            potency = pharm.get("potency_vs_morphine")
            if potency is not None:
                pot_score = min(25, (potency / 100) * 25)
                score += pot_score
                factors.append(f"Potency: {potency:.1f}x morphine")

            # Factor 4: lethal dose (lower = more dangerous)
            lethal = pharm.get("estimated_human_lethal_dose_mg")
            if lethal is not None and lethal > 0:
                ld_score = min(20, max(0, (1 - lethal / 2000) * 20))
                score += ld_score
                factors.append(f"Est. lethal dose: {lethal:.0f} mg")

            # Opioid component bonus (opioids are inherently more concerning)
            if is_opioid:
                score += 5
                factors.append("Opioid receptor ligand")

            scored.append({
                "name": ing.get("name", name),
                "is_opioid_component": is_opioid,
                "sensitivity_score": round(score, 1),
                "danger_level": pharm.get("danger_level", "Unknown"),
                "therapeutic_index": ti,
                "potency_vs_morphine": potency,
                "estimated_lethal_dose_mg": lethal,
                "factors": factors,
                "has_pharmacology_data": bool(pharm),
            })

        # Sort: highest score first
        scored.sort(key=lambda x: x["sensitivity_score"], reverse=True)

        most_sensitive = scored[0] if scored else None
        explanation = ""
        if most_sensitive:
            name = most_sensitive["name"]
            if most_sensitive["is_opioid_component"]:
                explanation = (
                    f"{name.title()} is the most sensitive ingredient because it is an "
                    f"opioid receptor ligand"
                )
            else:
                explanation = (
                    f"{name.title()} is flagged as the most sensitive ingredient"
                )
            if most_sensitive["factors"]:
                explanation += f" ({'; '.join(most_sensitive['factors'])})"
            explanation += "."
            dl = most_sensitive.get("danger_level", "Unknown")
            if dl in ("Extreme", "Very High", "High"):
                explanation += f" Its danger level is classified as {dl}."

        return {
            "drug_name": drug["drug_name"],
            "rxcui": drug["rxcui"],
            "ingredients": scored,
            "most_sensitive_ingredient": most_sensitive["name"] if most_sensitive else None,
            "explanation": explanation,
        }

    def assess_dose_risk(self, drug_name: str, daily_dose_mg: float) -> dict:
        """Assess risk for a given daily dose of an opioid.

        Returns a dict with: mme_assessment, lethal_dose_comparison,
        risk_factors, and recommendation.
        """
        ing = self._find_ingredient_name(drug_name)
        if not ing:
            return {"error": f"'{drug_name}' not found in pharmacology data."}

        pharm = self._ingredient_pharm[ing]
        mme_result = calculate_daily_mme(ing, daily_dose_mg)

        lethal = pharm.get("estimated_human_lethal_dose_mg")
        lethal_comparison = None
        if lethal and lethal > 0:
            pct = (daily_dose_mg / lethal) * 100
            lethal_comparison = {
                "estimated_lethal_dose_mg": lethal,
                "daily_dose_as_pct_of_lethal": round(pct, 2),
                "proximity_warning": pct > 30,
            }

        risk_factors = []
        if mme_result.get("risk_level") == "high":
            risk_factors.append(
                f"Daily MME of {mme_result['daily_mme']} exceeds CDC high-risk threshold (≥90 MME/day)"
            )
        elif mme_result.get("risk_level") == "increased":
            risk_factors.append(
                f"Daily MME of {mme_result['daily_mme']} exceeds CDC increased-risk threshold (≥50 MME/day)"
            )

        if lethal_comparison and lethal_comparison["proximity_warning"]:
            risk_factors.append(
                f"Daily dose is {lethal_comparison['daily_dose_as_pct_of_lethal']:.1f}% "
                f"of estimated human lethal dose ({lethal:.0f} mg)"
            )

        ti = pharm.get("therapeutic_index")
        if ti is not None and ti < 10:
            risk_factors.append(f"Narrow therapeutic index ({ti:.1f}) — small margin between effective and toxic doses")

        danger_level = pharm.get("danger_level", "Unknown")
        if danger_level in ("Extreme", "Very High"):
            risk_factors.append(f"Danger level: {danger_level}")

        nlp_entry = self._find_nlp_entry(drug_name)
        if nlp_entry:
            bw = nlp_entry.get("boxed_warning", {})
            if bw.get("present"):
                risk_factors.append("Drug carries a BOXED WARNING")

        if not risk_factors:
            recommendation = "Dose appears within normal clinical parameters. Standard monitoring applies."
        elif len(risk_factors) >= 3:
            recommendation = (
                "HIGH RISK: Multiple risk factors identified. Close clinical "
                "monitoring required. Consider dose reduction or alternative therapy."
            )
        else:
            recommendation = (
                "CAUTION: Risk factors identified. Enhanced monitoring recommended. "
                "Ensure naloxone co-prescribing per CDC guidelines."
            )

        return {
            "ingredient": ing,
            "daily_dose_mg": daily_dose_mg,
            "mme_assessment": mme_result,
            "lethal_dose_comparison": lethal_comparison,
            "risk_factors": risk_factors,
            "danger_level": danger_level,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Formatted brief for chat / LLM context
    # ------------------------------------------------------------------

    def format_brief_text(self, rxcui: str) -> str:
        """Generate a plain-text opioid intelligence brief suitable for chat."""
        brief = self.get_full_opioid_brief(rxcui)
        if "error" in brief:
            return brief["error"]

        ident = brief["identity"]
        lines = [
            f"# Opioid Intelligence Brief: {ident['drug_name']}",
            f"RxCUI: {ident['rxcui']}  |  Schedule: {ident.get('schedule') or 'N/A'}  |  "
            f"Category: {ident.get('opioid_category') or 'N/A'}",
            "",
        ]

        pharm = brief.get("pharmacology", {})
        if pharm:
            lines.append("## Pharmacology")
            if pharm.get("why_its_an_opioid"):
                lines.append(pharm["why_its_an_opioid"])
            potency = pharm.get("potency_vs_morphine")
            if potency is not None:
                lines.append(f"Potency vs morphine: {potency:.2f}x")
            hl = pharm.get("half_life_hours")
            if hl:
                lines.append(f"Half-life: {hl} hours")
            if pharm.get("active_metabolites"):
                lines.append(f"Active metabolites: {', '.join(pharm['active_metabolites'])}")
            lines.append("")

        safety = brief.get("safety", {})
        if safety:
            lines.append("## Safety Profile")
            lines.append(f"Danger level: {safety.get('danger_level', 'Unknown')}")
            leth = safety.get("estimated_human_lethal_dose_mg")
            if leth is not None:
                lines.append(f"Estimated human lethal dose: {leth:.1f} mg")
            ti = safety.get("therapeutic_index")
            if ti is not None:
                lines.append(f"Therapeutic index: {ti:.1f}")
            mme = safety.get("mme_conversion_factor")
            if mme:
                lines.append(f"MME conversion factor: {mme}")
            lines.append("")

        sig = brief.get("signals", {})
        if sig.get("consensus_signals"):
            lines.append("## FAERS Safety Signals")
            lines.append(f"Consensus signals: {sig['consensus_signals']} of {sig['total_signals']} tested")
            for s in sig.get("top_signals", []):
                lines.append(f"  - {s['reaction']}: {s['report_count']} reports ({s['methods_flagging']}/3 methods)")
            lines.append("")

        lbl = brief.get("label_highlights", {})
        if lbl:
            lines.append("## Label Highlights")
            if lbl.get("has_boxed_warning"):
                lines.append(f"BOXED WARNING: Yes ({lbl.get('boxed_warning_count', 0)} paragraphs)")
                if lbl.get("key_warnings"):
                    lines.append(f"Key warnings: {', '.join(lbl['key_warnings'][:5])}")
            if lbl.get("rems_required"):
                lines.append(f"REMS: {lbl.get('rems_type', 'Yes')}")
            if lbl.get("drug_interactions_benzo"):
                lines.append("Benzodiazepine interaction warning: YES")
            if lbl.get("overdose_symptoms"):
                lines.append(f"Overdose symptoms: {', '.join(lbl['overdose_symptoms'])}")

        return "\n".join(lines)
