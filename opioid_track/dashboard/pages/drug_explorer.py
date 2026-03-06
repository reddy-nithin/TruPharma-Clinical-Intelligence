"""
Drug Explorer Page — Deep dive into individual opioid drugs.
"""

import streamlit as st
from opioid_track.dashboard.components.charts import create_receptor_bar


def _metric_card(label: str, value, css_class: str = ""):
    cls = f"metric-card {css_class}".strip()
    st.markdown(
        f'<div class="{cls}"><h3>{label}</h3>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _find_ingredient_data(pharma: dict, ingredient_name: str) -> dict | None:
    ip = pharma.get("ingredient_pharmacology", {})
    return ip.get(ingredient_name.lower())


def _get_drug_signals(signals: dict, drug_name: str) -> list[dict]:
    all_signals = signals.get("signals", [])
    return [s for s in all_signals if drug_name.lower() in s.get("drug_name", "").lower()]


def _get_nlp_data(nlp: dict, drug_name: str) -> dict | None:
    for d in nlp.get("drug_label_insights", []):
        if drug_name.lower() in d.get("drug_name", "").lower():
            return d
    return None


def render(data: dict):
    st.markdown("<h1 class='section-header'>Drug Explorer</h1>", unsafe_allow_html=True)

    registry = data.get("registry")
    pharmacology = data.get("pharmacology")
    signals = data.get("signals")
    nlp_insights = data.get("nlp_insights")

    if not registry:
        st.warning("Registry data not available.")
        return

    # Build searchable drug list
    drugs = registry.get("opioid_drugs", [])
    ingredient_names = set()
    drug_index = {}
    for d in drugs:
        name = d.get("drug_name", "")
        drug_index[name] = d
        for ing in d.get("active_ingredients", []):
            if ing.get("is_opioid_component"):
                ingredient_names.add(ing["name"].lower())

    # Search
    search = st.text_input("Search by drug name, ingredient, or RxCUI",
                           placeholder="e.g. oxycodone, fentanyl, 7804")

    matching = []
    if search:
        search_lower = search.lower().strip()
        for name, d in drug_index.items():
            if (search_lower in name.lower()
                    or search_lower == d.get("rxcui", "")
                    or any(search_lower in i.get("name", "").lower()
                           for i in d.get("active_ingredients", []))):
                matching.append(name)
        matching = sorted(matching)[:50]

    if not matching and not search:
        popular = [n for n in drug_index if any(k in n.lower()
                   for k in ("oxycodone", "fentanyl", "morphine", "hydrocodone",
                             "buprenorphine", "methadone", "tramadol", "codeine"))]
        matching = sorted(popular)[:30]

    if not matching:
        st.info("No drugs match your search. Try a different term.")
        return

    selected_name = st.selectbox("Select a drug", matching)
    drug = drug_index.get(selected_name)
    if not drug:
        return

    # --- Drug Identity Card ---
    st.markdown("<h2 class='section-header'>Identity</h2>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card("Drug Name", drug["drug_name"][:40])
    with col2:
        _metric_card("Schedule", drug.get("schedule") or "None")
    with col3:
        _metric_card("Category", (drug.get("opioid_category") or "Unknown").title())
    with col4:
        _metric_card("RxCUI", drug["rxcui"])

    # Active ingredients
    opioid_ings = [i for i in drug.get("active_ingredients", []) if i.get("is_opioid_component")]
    non_opioid = [i for i in drug.get("active_ingredients", [])
                  if not i.get("is_opioid_component") and i.get("tty") == "IN"]

    if opioid_ings:
        ing_text = ", ".join(f"**{i['name']}** (opioid)" for i in opioid_ings)
        if non_opioid:
            ing_text += ", " + ", ".join(i["name"] for i in non_opioid)
        st.markdown(f"**Active Ingredients:** {ing_text}")

    # --- Pharmacology Panel ---
    if pharmacology and opioid_ings:
        primary_ing = opioid_ings[0]["name"]
        ing_data = _find_ingredient_data(pharmacology, primary_ing)

        if ing_data:
            st.markdown("<h2 class='section-header'>Pharmacology</h2>",
                        unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])
            with col1:
                affinities = ing_data.get("receptor_affinities", {})
                fig = create_receptor_bar(affinities)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                potency = ing_data.get("potency_vs_morphine")
                if potency:
                    _metric_card("Potency vs Morphine", f"{potency:.1f}x",
                                 "danger-high" if potency > 10 else "")

                hl = ing_data.get("half_life_hours")
                if hl:
                    _metric_card("Half-Life", f"{hl} hours")

                mw = ing_data.get("molecular_weight")
                if mw:
                    _metric_card("Molecular Weight", f"{mw} g/mol")

            # Why it's an opioid
            why = ing_data.get("why_its_an_opioid")
            if why:
                st.info(why)

            # Metabolism
            met = ing_data.get("metabolism")
            if met:
                st.markdown(f"**Metabolism:** {met[:300]}")

    # --- Safety Panel ---
    if pharmacology and opioid_ings:
        ing_data = _find_ingredient_data(pharmacology, opioid_ings[0]["name"])
        if ing_data:
            st.markdown("<h2 class='section-header'>Safety Profile</h2>",
                        unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mme = drug.get("mme_conversion_factor")
                _metric_card("MME Factor", f"{mme}" if mme else "N/A")
            with col2:
                danger = ing_data.get("danger_level", "Unknown")
                css = ("danger-high" if danger in ("Extreme", "Very High", "High")
                       else "danger-moderate" if danger == "Moderate" else "danger-low")
                _metric_card("Danger Level", danger, css)
            with col3:
                ti = ing_data.get("therapeutic_index")
                _metric_card("Therapeutic Index", f"{ti:.0f}" if ti else "N/A")
            with col4:
                lethal = ing_data.get("estimated_human_lethal_dose_mg")
                _metric_card("Est. Lethal Dose (70kg)",
                             f"{lethal:.0f} mg" if lethal else "Unknown")

            # LD50 table
            ld50s = ing_data.get("ld50_data", [])
            if ld50s:
                st.markdown("**LD50 Data:**")
                rows = []
                for entry in ld50s[:5]:
                    rows.append({
                        "Species": entry.get("species", "?").capitalize(),
                        "Route": entry.get("route", "?").capitalize(),
                        "LD50 (mg/kg)": entry.get("ld50_mg_kg", "?"),
                        "Source": entry.get("source", "?"),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- FAERS Signals Panel ---
    if signals and opioid_ings:
        drug_sigs = []
        for ing in opioid_ings:
            drug_sigs.extend(_get_drug_signals(signals, ing["name"]))

        if drug_sigs:
            st.markdown("<h2 class='section-header'>FAERS Safety Signals</h2>",
                        unsafe_allow_html=True)

            consensus = [s for s in drug_sigs if s.get("consensus_signal")]
            partial = [s for s in drug_sigs if not s.get("consensus_signal")
                       and s.get("methods_flagging", 0) >= 1]

            if consensus:
                st.markdown(f"**{len(consensus)} Consensus Signals** (flagged by 2+ methods)")
                rows = []
                for s in sorted(consensus, key=lambda x: -x.get("report_count", 0))[:15]:
                    rows.append({
                        "Reaction": s["reaction"],
                        "Reports": f"{s.get('report_count', 0):,}",
                        "Methods": f"{s.get('methods_flagging', 0)}/3",
                        "PRR": f"{s.get('prr', {}).get('value', 0):.1f}",
                        "ROR": f"{s.get('ror', {}).get('value', 0):.1f}",
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- Label Highlights Panel ---
    if nlp_insights and opioid_ings:
        nlp_data = None
        for ing in opioid_ings:
            nlp_data = _get_nlp_data(nlp_insights, ing["name"])
            if nlp_data:
                break

        if nlp_data:
            st.markdown("<h2 class='section-header'>Label Highlights (NLP)</h2>",
                        unsafe_allow_html=True)
            st.caption("Source: CDCgov/Opioid_Involvement_NLP adapted for DailyMed SPL labels")

            # Boxed warning
            bw = nlp_data.get("boxed_warning", {})
            if bw.get("present"):
                with st.container():
                    st.markdown(
                        f"<div style='border: 2px solid {st.get_option('theme.primaryColor') or '#ef4444'}; "
                        f"border-radius: 8px; padding: 1rem; background: rgba(239,68,68,0.08);'>"
                        f"<strong>BOXED WARNING</strong> ({bw.get('paragraph_count', 0)} sections)<br>"
                        f"Key warnings: {', '.join(bw.get('key_warnings', []))}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            col1, col2, col3 = st.columns(3)
            with col1:
                rems = nlp_data.get("rems", {})
                _metric_card("REMS Required",
                             "Yes" if rems.get("rems_required") else "No",
                             "danger-high" if rems.get("rems_required") else "")
            with col2:
                dosage = nlp_data.get("dosage", {})
                _metric_card("Max Daily Dose",
                             f"{dosage.get('max_daily_dose_mg', 'N/A')} mg")
            with col3:
                interactions = nlp_data.get("drug_interactions", {})
                _metric_card("Benzo Warning",
                             "Yes" if interactions.get("benzo_warning") else "No",
                             "danger-high" if interactions.get("benzo_warning") else "")

            # CYP interactions
            cyps = nlp_data.get("drug_interactions", {}).get("cyp_interactions", [])
            if cyps:
                st.markdown(f"**CYP Enzyme Interactions:** {', '.join(cyps)}")

            # Overdose info
            od = nlp_data.get("overdosage", {})
            if od.get("naloxone_rescue_dose"):
                st.markdown(f"**Naloxone Rescue Dose:** {od['naloxone_rescue_dose']}")
            if od.get("symptoms"):
                st.markdown(f"**Overdose Symptoms:** {', '.join(od['symptoms'][:8])}")

    # --- Products containing same ingredient ---
    if pharmacology and opioid_ings:
        ing_data = _find_ingredient_data(pharmacology, opioid_ings[0]["name"])
        if ing_data:
            products = ing_data.get("products_containing", [])
            if products and len(products) > 1:
                st.markdown("<h2 class='section-header'>Other Products</h2>",
                            unsafe_allow_html=True)
                st.caption(f"{len(products)} products contain {opioid_ings[0]['name']}")
                rows = []
                for p in products[:20]:
                    rows.append({
                        "Product": p.get("drug_name", ""),
                        "RxCUI": p.get("rxcui", ""),
                        "Schedule": p.get("schedule", ""),
                        "Type": p.get("tty", ""),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
