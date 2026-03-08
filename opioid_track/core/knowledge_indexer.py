"""
Knowledge Indexer — RAG-Ready Chunk Generator
==============================================
Generates text chunks from all Tier 1–3 opioid data for use in
any RAG (Retrieval-Augmented Generation) system.

Outputs individual .txt files + manifest.json into config.KNOWLEDGE_CHUNKS_DIR.
Does NOT modify the main TruPharma RAG index.

Usage:
    python -m opioid_track.core.knowledge_indexer
"""

import json
import os
import re
from datetime import datetime, timezone

from opioid_track import config


def _load_json(path: str) -> dict | list:
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (≈ 1 token per 4 chars for English)."""
    return max(1, len(text) // 4)


def _save_chunk(chunks_dir: str, filename: str, text: str, manifest: list, **meta):
    filepath = os.path.join(chunks_dir, filename)
    with open(filepath, "w") as f:
        f.write(text)
    manifest.append({
        "filename": filename,
        "token_estimate": _estimate_tokens(text),
        **meta,
    })


# ------------------------------------------------------------------
# Classification chunks (from registry)
# ------------------------------------------------------------------

def generate_classification_chunks(registry: dict, chunks_dir: str, manifest: list):
    """Generate broad classification knowledge chunks."""

    drugs = registry.get("opioid_drugs", [])

    # Opioid categories overview
    categories = {}
    for d in drugs:
        cat = d.get("opioid_category", "unknown")
        categories.setdefault(cat, [])
        for ing in d.get("active_ingredients", []):
            if ing.get("is_opioid_component"):
                n = ing["name"].lower()
                if n not in categories[cat]:
                    categories[cat].append(n)

    text = "OPIOID CLASSIFICATION CATEGORIES\n\n"
    text += (
        "Opioids are classified by chemical origin into several categories. "
        "This classification matters for clinical pharmacology, regulation, and "
        "risk assessment.\n\n"
    )
    for cat, ingredients in sorted(categories.items()):
        text += f"- {cat.title()}: {', '.join(sorted(set(ingredients))[:8])}\n"
    text += (
        "\nNatural opioids (e.g., morphine, codeine) are derived from the opium poppy. "
        "Semi-synthetic opioids (e.g., oxycodone, hydrocodone) are chemically modified from natural precursors. "
        "Synthetic opioids (e.g., fentanyl, methadone, tramadol) are entirely laboratory-created. "
        "Combination products pair opioids with non-opioid analgesics (acetaminophen, ibuprofen) or "
        "antagonists (naloxone for abuse deterrence). Treatment/recovery agents (buprenorphine, "
        "methadone for MAT) leverage partial agonism or long half-lives to stabilize patients.\n"
    )
    _save_chunk(chunks_dir, "classification_categories.txt", text, manifest,
                type="classification", drug_name=None, rxcui=None)

    # Receptor system
    text = "THE OPIOID RECEPTOR SYSTEM\n\n"
    text += (
        "Opioids exert their effects through four G-protein coupled receptors:\n\n"
        "1. Mu receptor (OPRM1, MOR) — Primary mediator of analgesia, euphoria, "
        "respiratory depression, and physical dependence. Most clinically used "
        "opioids target mu. High mu affinity (low Ki value) correlates with potency.\n\n"
        "2. Kappa receptor (OPRK1, KOR) — Mediates spinal analgesia, sedation, and "
        "dysphoria. Kappa agonists (pentazocine, butorphanol) produce less euphoria "
        "and have lower abuse potential but cause dysphoric side effects.\n\n"
        "3. Delta receptor (OPRD1, DOR) — Modulates pain, mood, and cardioprotection. "
        "Few clinical drugs primarily target delta, though many mu agonists have "
        "secondary delta activity.\n\n"
        "4. Nociceptin/OFQ receptor (OPRL1, NOP) — Involved in pain modulation, "
        "anxiety, and feeding. The NOP receptor has complex, sometimes anti-opioid "
        "effects. Buprenorphine has notable NOP activity.\n\n"
        "Receptor affinity is measured as Ki (inhibition constant) in nanomolar (nM). "
        "Lower Ki = higher affinity = more potent binding. For example, fentanyl has "
        "a mu Ki of ~0.08 nM while morphine's is ~1.8 nM, making fentanyl roughly "
        "20x more potent at the receptor level.\n"
    )
    _save_chunk(chunks_dir, "receptor_system.txt", text, manifest,
                type="classification", drug_name=None, rxcui=None)

    # DEA scheduling
    schedules = {}
    for d in drugs:
        sched = d.get("schedule", "") or "Unscheduled"
        schedules.setdefault(sched, 0)
        schedules[sched] += 1

    text = "DEA SCHEDULING FOR OPIOIDS\n\n"
    text += (
        "The U.S. Drug Enforcement Administration (DEA) classifies controlled "
        "substances into five schedules based on accepted medical use, abuse "
        "potential, and dependence liability.\n\n"
    )
    sched_desc = {
        "CII": "Schedule II — High abuse potential, severe dependence. Includes morphine, fentanyl, oxycodone, hydrocodone, methadone.",
        "CIII": "Schedule III — Moderate abuse potential. Includes buprenorphine products (Suboxone), codeine combinations.",
        "CIV": "Schedule IV — Lower abuse potential. Includes tramadol.",
        "CV": "Schedule V — Lowest scheduled abuse potential. Includes low-dose codeine cough preparations.",
    }
    for sched, desc in sched_desc.items():
        count = schedules.get(sched, 0)
        text += f"{desc} ({count} products in registry)\n\n"
    text += (
        f"Unscheduled/other: {schedules.get('Unscheduled', 0) + schedules.get('', 0)} products\n"
    )
    _save_chunk(chunks_dir, "dea_scheduling.txt", text, manifest,
                type="classification", drug_name=None, rxcui=None)

    # All opioids by category
    text = "COMPLETE OPIOID INGREDIENT LIST BY CATEGORY\n\n"
    for cat, ingredients in sorted(categories.items()):
        unique = sorted(set(ingredients))
        text += f"### {cat.title()} ({len(unique)} ingredients)\n"
        for ing in unique:
            text += f"  - {ing}\n"
        text += "\n"
    _save_chunk(chunks_dir, "opioid_ingredients_list.txt", text, manifest,
                type="classification", drug_name=None, rxcui=None)


# ------------------------------------------------------------------
# Per-ingredient pharmacology chunks
# ------------------------------------------------------------------

def generate_pharmacology_chunks(pharm_data: dict, chunks_dir: str, manifest: list):
    """Generate one chunk per ingredient from pharmacology data."""
    ingredients = pharm_data.get("ingredient_pharmacology", {})

    for name, data in ingredients.items():
        lines = [f"PHARMACOLOGY: {name.upper()}\n"]

        rxcui = data.get("rxcui_ingredient", "")
        chembl = data.get("chembl_id", "")
        cid = data.get("pubchem_cid", "")
        lines.append(f"Identifiers: RxCUI={rxcui}, ChEMBL={chembl}, PubChem CID={cid}")

        mw = data.get("molecular_weight")
        formula = data.get("molecular_formula")
        if mw or formula:
            lines.append(f"Molecular: {formula or 'N/A'}, MW={mw or 'N/A'}")

        affinities = data.get("receptor_affinities", {})
        if affinities:
            lines.append("\nReceptor Binding Affinities:")
            for receptor, aff in affinities.items():
                ki = aff.get("ki_nM")
                src = aff.get("source", "")
                lines.append(f"  - {receptor}: Ki = {ki} nM (source: {src})")

        potency = data.get("potency_vs_morphine")
        if potency is not None:
            lines.append(f"\nPotency vs morphine: {potency:.2f}x")

        why = data.get("why_its_an_opioid", "")
        if why:
            lines.append(f"\n{why}")

        hl = data.get("half_life_hours")
        if hl:
            lines.append(f"\nHalf-life: {hl} hours")
        metab = data.get("metabolism", "")
        if metab:
            lines.append(f"Metabolism: {metab[:300]}")
        metabolites = data.get("active_metabolites", [])
        if metabolites:
            lines.append(f"Active metabolites: {', '.join(metabolites)}")

        ld50 = data.get("ld50_data", [])
        if ld50:
            lines.append("\nToxicology:")
            for entry in ld50[:3]:
                lines.append(
                    f"  LD50 ({entry.get('species', '?')}, {entry.get('route', '?')}): "
                    f"{entry.get('ld50_mg_kg', '?')} mg/kg"
                )

        leth = data.get("estimated_human_lethal_dose_mg")
        if leth is not None:
            lines.append(f"  Estimated human lethal dose: {leth:.1f} mg")
        ti = data.get("therapeutic_index")
        if ti is not None:
            lines.append(f"  Therapeutic index: {ti:.1f}")
        dl = data.get("danger_level", "Unknown")
        lines.append(f"  Danger level: {dl}")

        text = "\n".join(lines)
        _save_chunk(
            chunks_dir, f"ingredient_{name}.txt", text, manifest,
            type="pharmacology", drug_name=name, rxcui=rxcui,
        )


# ------------------------------------------------------------------
# Per-drug safety chunks (from NLP insights)
# ------------------------------------------------------------------

def generate_safety_chunks(nlp_data: dict, chunks_dir: str, manifest: list):
    """Generate one chunk per drug from NLP-mined label data."""
    insights = nlp_data.get("drug_label_insights", [])

    for entry in insights:
        drug_name = entry.get("drug_name", "unknown")
        rxcui = entry.get("rxcui", "")
        safe_name = re.sub(r'[^a-z0-9]+', '_', drug_name.lower()).strip('_')[:60]

        lines = [f"DRUG SAFETY PROFILE: {drug_name}\n"]
        lines.append(f"RxCUI: {rxcui}")
        lines.append(f"Category: {entry.get('opioid_category', 'N/A')}")
        lines.append(f"Opioid ingredients: {', '.join(entry.get('opioid_ingredients', []))}")

        bw = entry.get("boxed_warning", {})
        if bw.get("present"):
            lines.append(f"\nBOXED WARNING (Black Box): Yes")
            warnings = bw.get("key_warnings", [])
            if warnings:
                lines.append(f"Key warnings: {', '.join(warnings)}")
            full = bw.get("full_text", "")
            if full:
                lines.append(f"Warning text: {full[:400]}")
        else:
            lines.append("\nBoxed Warning: None")

        dosage = entry.get("dosage", {})
        if dosage.get("starting_dose"):
            lines.append(f"\nStarting dose: {dosage['starting_dose']}")
        if dosage.get("max_daily_dose_mg"):
            lines.append(f"Max daily dose: {dosage['max_daily_dose_mg']} mg")
        mme = entry.get("max_daily_mme")
        if mme:
            lines.append(f"Max daily MME: {mme}")

        rems = entry.get("rems", {})
        if rems.get("rems_required"):
            lines.append(f"\nREMS Required: {rems.get('rems_type', 'Yes')}")

        di = entry.get("drug_interactions", {})
        if di.get("benzo_warning"):
            lines.append("Benzodiazepine co-administration warning: YES")
        cyp = di.get("cyp_interactions", [])
        if cyp:
            lines.append(f"CYP enzyme interactions: {', '.join(cyp)}")

        od = entry.get("overdosage", {})
        symptoms = od.get("symptoms", [])
        if symptoms:
            lines.append(f"\nOverdose symptoms: {', '.join(symptoms)}")
        nalox = od.get("naloxone_rescue_dose")
        if nalox:
            lines.append(f"Naloxone rescue dose: {nalox}")

        ad = entry.get("abuse_dependence", {})
        sched = ad.get("schedule")
        if sched:
            lines.append(f"DEA Schedule: {sched}")

        ar = entry.get("adverse_reactions", {})
        safety_terms = ar.get("safety_terms_detected", [])
        if safety_terms:
            lines.append(f"\nSafety terms in label: {', '.join(safety_terms)}")

        lines.append(f"\nSource: DailyMed SPL label, NLP via CDCgov/Opioid_Involvement_NLP")

        text = "\n".join(lines)
        _save_chunk(
            chunks_dir, f"safety_{safe_name}.txt", text, manifest,
            type="safety", drug_name=drug_name, rxcui=rxcui,
        )


# ------------------------------------------------------------------
# Epidemiological context chunks (from Tier 2 data)
# ------------------------------------------------------------------

def generate_epi_chunks(
    mortality_data: dict,
    prescribing_data: dict,
    chunks_dir: str,
    manifest: list,
):
    """Generate epidemiological context chunks from CDC and CMS data."""

    # Three waves of the opioid epidemic
    annual = mortality_data.get("annual_national", [])
    if annual:
        text = "THE THREE WAVES OF THE OPIOID EPIDEMIC\n\n"
        text += (
            "The U.S. opioid crisis has unfolded in three overlapping waves:\n\n"
            "Wave 1 (1990s–2010): Prescription opioid overdoses. Driven by aggressive "
            "marketing of OxyContin and liberal prescribing. Deaths from natural and "
            "semi-synthetic opioids (T40.2) — oxycodone, hydrocodone — dominated.\n\n"
            "Wave 2 (2010–2013): Heroin overdoses. As prescription opioids became harder "
            "to obtain, users transitioned to cheaper heroin. Heroin deaths (T40.1) surged.\n\n"
            "Wave 3 (2013–present): Synthetic opioid overdoses. Illicitly manufactured "
            "fentanyl and its analogues drove unprecedented death tolls. Synthetic opioid "
            "deaths (T40.4) now account for the majority of overdose fatalities.\n\n"
            "CDC VSRR National Data:\n"
        )
        for yr in annual:
            year = yr.get("year")
            wave = yr.get("opioid_wave", "")
            total = yr.get("total_overdose_deaths") or 0
            by_type = yr.get("by_opioid_type", {})
            all_opioid = by_type.get("all_opioids") or 0
            synth = by_type.get("synthetic_fentanyl_T40.4") or 0
            heroin = by_type.get("heroin_T40.1") or 0
            nat = by_type.get("natural_semisynthetic_T40.2") or 0
            text += (
                f"  {year}: {total:,} total overdose deaths, {all_opioid:,} opioid "
                f"(synthetic={synth:,}, heroin={heroin:,}, Rx opioids={nat:,}) — {wave}\n"
            )

        _save_chunk(chunks_dir, "epi_three_waves.txt", text, manifest,
                    type="epidemiology", drug_name=None, rxcui=None)

    # Top states by prescribing rate
    by_geo = prescribing_data.get("by_geography", [])
    if by_geo:
        state_rates = {}
        for rec in by_geo:
            if rec.get("geo_level") == "state" and rec.get("year") == 2023:
                state = rec.get("state", "")
                rate = rec.get("opioid_prescribing_rate")
                if state and rate is not None:
                    if state not in state_rates or rate > state_rates[state]:
                        state_rates[state] = rate

        if state_rates:
            sorted_states = sorted(state_rates.items(), key=lambda x: x[1], reverse=True)
            text = "TOP STATES BY OPIOID PRESCRIBING RATE (2023, CMS Medicare Part D)\n\n"
            for i, (state, rate) in enumerate(sorted_states[:20], 1):
                text += f"  {i}. {state}: {rate:.2f} prescriptions per enrollee\n"
            text += (
                f"\nLowest: {sorted_states[-1][0]} ({sorted_states[-1][1]:.2f})\n"
                f"National context: Higher prescribing rates correlate with greater "
                f"opioid exposure and overdose risk at the population level.\n"
            )
            _save_chunk(chunks_dir, "epi_top_prescribing_states.txt", text, manifest,
                        type="epidemiology", drug_name=None, rxcui=None)

    # Top states by death rate (from state_profiles in mortality)
    state_profiles = mortality_data.get("state_profiles", [])
    if state_profiles:
        latest_year = max(
            (s.get("latest_year", 0) for s in state_profiles),
            default=0,
        )
        death_rates = []
        for sp in state_profiles:
            state = sp.get("state", "")
            yearly = sp.get("yearly_data", [])
            for yr_data in yearly:
                if yr_data.get("year") == latest_year:
                    rate = yr_data.get("death_rate_per_100k")
                    if rate is not None:
                        death_rates.append((state, rate))

        if death_rates:
            death_rates.sort(key=lambda x: x[1], reverse=True)
            text = f"TOP STATES BY OPIOID DEATH RATE ({latest_year})\n\n"
            for i, (state, rate) in enumerate(death_rates[:20], 1):
                text += f"  {i}. {state}: {rate:.1f} deaths per 100,000\n"
            text += (
                "\nOpioid death rates vary dramatically by state, reflecting "
                "differences in drug supply, prescribing patterns, treatment "
                "availability, and social determinants of health.\n"
            )
            _save_chunk(chunks_dir, "epi_top_death_rate_states.txt", text, manifest,
                        type="epidemiology", drug_name=None, rxcui=None)


# ------------------------------------------------------------------
# FAERS signal chunks
# ------------------------------------------------------------------

def generate_signal_chunks(signal_data: dict, chunks_dir: str, manifest: list):
    """Generate one chunk per drug summarizing its FAERS consensus signals."""
    signals = signal_data.get("signals", [])
    if not signals:
        return

    by_drug = {}
    for s in signals:
        drug = s.get("drug_name", "unknown")
        by_drug.setdefault(drug, []).append(s)

    for drug_name, drug_sigs in by_drug.items():
        consensus = [s for s in drug_sigs if s.get("consensus_signal")]
        if not consensus:
            continue

        lines = [f"FAERS SAFETY SIGNALS: {drug_name.upper()}\n"]
        lines.append(
            f"Total signal pairs tested: {len(drug_sigs)}, "
            f"Consensus signals (≥2 methods): {len(consensus)}"
        )
        lines.append(
            "Methods: PRR (Proportional Reporting Ratio), ROR (Reporting Odds Ratio), "
            "MGPS/EBGM (Multi-item Gamma Poisson Shrinker)\n"
        )

        for s in sorted(consensus, key=lambda x: x.get("report_count", 0), reverse=True):
            reaction = s.get("reaction", "")
            count = s.get("report_count", 0)
            n_methods = s.get("methods_flagging", 0)
            prr = s.get("prr", {}).get("value")
            ror = s.get("ror", {}).get("value")
            ebgm = s.get("mgps", {}).get("ebgm")

            metrics = []
            if prr:
                metrics.append(f"PRR={prr:.2f}")
            if ror:
                metrics.append(f"ROR={ror:.2f}")
            if ebgm:
                metrics.append(f"EBGM={ebgm:.2f}")

            lines.append(
                f"  - {reaction}: {count:,} reports, {n_methods}/3 methods flagging"
            )
            if metrics:
                lines.append(f"    Signal strength: {', '.join(metrics)}")

        lines.append(
            f"\nSource: FDA FAERS via OpenFDA, signal detection per "
            f"PharmacologicallyActive disproportionality analysis"
        )

        text = "\n".join(lines)
        safe_name = re.sub(r'[^a-z0-9]+', '_', drug_name.lower()).strip('_')
        _save_chunk(
            chunks_dir, f"signals_{safe_name}.txt", text, manifest,
            type="faers_signals", drug_name=drug_name, rxcui=None,
        )


# ------------------------------------------------------------------
# Demographic chunks
# ------------------------------------------------------------------

def generate_demographics_chunks(demographics_data: dict, chunks_dir: str, manifest: list):
    """Generate knowledge chunks from demographics data."""
    if not demographics_data:
        return

    meta = demographics_data.get("metadata", {})
    by_age = demographics_data.get("by_age_group", [])
    by_sex = demographics_data.get("by_sex", [])
    by_race = demographics_data.get("by_race_ethnicity", [])

    # --- Age breakdown chunk ---
    if by_age:
        text = f"OPIOID OVERDOSE DEATHS BY AGE GROUP ({meta.get('data_year', '?')})\n\n"
        total = sum(d["deaths"] for d in by_age)
        text += f"Total opioid-involved overdose deaths: {total:,}\n\n"
        for d in by_age:
            text += (
                f"  {d['group']}: {d['deaths']:,} deaths "
                f"({d['rate_per_100k']}/100K, {d['pct_of_total']}% of total)\n"
            )
        text += (
            "\nAdults aged 25-44 account for nearly 47% of all opioid overdose deaths. "
            "The 35-44 age group has the highest rate at 43.9 per 100K.\n"
        )
        _save_chunk(chunks_dir, "demo_by_age.txt", text, manifest,
                    type="demographics", drug_name=None, rxcui=None)

    # --- Sex breakdown chunk ---
    if by_sex:
        text = f"OPIOID OVERDOSE DEATHS BY SEX ({meta.get('data_year', '?')})\n\n"
        for d in by_sex:
            text += (
                f"  {d['sex']}: {d['deaths']:,} deaths "
                f"({d['rate_per_100k']}/100K, {d['pct_of_total']}% of total)\n"
            )
        text += (
            "\nMales die from opioid overdoses at 2.3x the rate of females "
            "(33.1 vs 14.2 per 100K). Males account for nearly 70% of all "
            "opioid overdose deaths.\n"
        )
        _save_chunk(chunks_dir, "demo_by_sex.txt", text, manifest,
                    type="demographics", drug_name=None, rxcui=None)

    # --- Race/ethnicity breakdown chunk ---
    if by_race:
        text = f"OPIOID OVERDOSE DEATHS BY RACE/ETHNICITY ({meta.get('data_year', '?')})\n\n"
        for d in by_race:
            text += (
                f"  {d['group']}: {d['deaths']:,} deaths "
                f"({d['rate_per_100k']}/100K, {d['pct_of_total']}% of total)\n"
            )
        text += (
            "\nAmerican Indian/Alaska Native populations have the highest "
            "age-adjusted rate (44.3/100K) despite representing only 1.9% of "
            "total deaths. Black Non-Hispanic populations have the second-highest "
            "rate (40.8/100K). White Non-Hispanic populations have the highest "
            "absolute number of deaths due to larger population size. Racial "
            "disparities in opioid overdose deaths have widened significantly "
            "since 2015.\n"
        )
        _save_chunk(chunks_dir, "demo_by_race.txt", text, manifest,
                    type="demographics", drug_name=None, rxcui=None)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def build_knowledge_chunks():
    """Generate all knowledge chunks and manifest."""
    chunks_dir = config.KNOWLEDGE_CHUNKS_DIR
    os.makedirs(chunks_dir, exist_ok=True)

    manifest: list[dict] = []

    print("Loading data files...")
    registry = _load_json(config.REGISTRY_OUTPUT)
    pharm = _load_json(config.PHARMACOLOGY_OUTPUT)
    nlp = _load_json(config.NLP_INSIGHTS_OUTPUT)
    signals = _load_json(config.SIGNAL_RESULTS_OUTPUT)
    mortality = _load_json(config.CDC_MORTALITY_OUTPUT)
    prescribing = _load_json(config.CMS_PRESCRIBING_OUTPUT)

    print("Generating classification chunks...")
    generate_classification_chunks(registry, chunks_dir, manifest)

    print("Generating pharmacology chunks...")
    generate_pharmacology_chunks(pharm, chunks_dir, manifest)

    print("Generating safety chunks...")
    generate_safety_chunks(nlp, chunks_dir, manifest)

    print("Generating epidemiological chunks...")
    generate_epi_chunks(mortality, prescribing, chunks_dir, manifest)

    print("Generating FAERS signal chunks...")
    generate_signal_chunks(signals, chunks_dir, manifest)

    demographics = _load_json(config.DEMOGRAPHICS_OUTPUT)
    if demographics:
        print("Generating demographics chunks...")
        generate_demographics_chunks(demographics, chunks_dir, manifest)

    manifest_path = os.path.join(chunks_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_chunks": len(manifest),
            "total_tokens_estimate": sum(c["token_estimate"] for c in manifest),
            "chunks": manifest,
        }, f, indent=2)

    print(f"\nKnowledge indexer complete:")
    print(f"  Chunks generated: {len(manifest)}")
    print(f"  Total estimated tokens: {sum(c['token_estimate'] for c in manifest):,}")
    print(f"  Output directory: {chunks_dir}")
    print(f"  Manifest: {manifest_path}")


def main():
    build_knowledge_chunks()


if __name__ == "__main__":
    main()
