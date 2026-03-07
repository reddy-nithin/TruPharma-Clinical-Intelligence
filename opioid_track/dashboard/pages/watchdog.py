"""
Watchdog Tools Page — Interactive opioid intelligence tools powered by OpioidWatchdog.
"""

import streamlit as st

from opioid_track.agents.opioid_watchdog import OpioidWatchdog


def _metric_card(label: str, value, css_class: str = ""):
    cls = f"metric-card {css_class}".strip()
    st.markdown(
        f'<div class="{cls}"><h3>{label}</h3>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _get_ingredient_list(data: dict) -> list[str]:
    pharma = data.get("pharmacology") or {}
    ip = pharma.get("ingredient_pharmacology", {})
    return sorted(ip.keys())


@st.cache_resource
def _get_watchdog(data_key: str) -> OpioidWatchdog:
    """Singleton watchdog, keyed to bust cache if data changes."""
    return OpioidWatchdog()


def render(data: dict):
    st.markdown("<h1 class='section-header'>Watchdog Tools</h1>", unsafe_allow_html=True)
    st.caption("Interactive intelligence tools powered by the OpioidWatchdog agent")

    pharmacology = data.get("pharmacology")
    if not pharmacology:
        st.warning("Pharmacology data not available. Run pharmacology_fetcher first.")
        return

    watchdog = _get_watchdog("v1")
    ingredients = _get_ingredient_list(data)

    if not ingredients:
        st.warning("No ingredient data found.")
        return

    tab1, tab2, tab3 = st.tabs([
        "Dose Risk Calculator",
        "Danger Comparator",
        "Intelligence Brief",
    ])

    # ------------------------------------------------------------------
    # Panel A: Dose Risk Calculator
    # ------------------------------------------------------------------
    with tab1:
        st.markdown("<h2 class='section-header'>Dose Risk Calculator</h2>",
                    unsafe_allow_html=True)
        st.markdown(
            "Assess the risk of a specific daily opioid dose using MME calculations, "
            "lethal dose proximity, and CDC guidelines."
        )

        col_input1, col_input2 = st.columns(2)
        with col_input1:
            drug_choice = st.selectbox(
                "Opioid ingredient",
                ingredients,
                format_func=str.title,
                key="dose_drug",
            )
        with col_input2:
            daily_dose = st.number_input(
                "Daily dose (mg)",
                min_value=0.1,
                max_value=5000.0,
                value=30.0,
                step=5.0,
                key="dose_mg",
            )

        if st.button("Assess Risk", type="primary", key="assess_btn"):
            result = watchdog.assess_dose_risk(drug_choice, daily_dose)

            if "error" in result:
                st.error(result["error"])
            else:
                st.divider()

                mme = result.get("mme_assessment", {})
                daily_mme = mme.get("daily_mme")
                risk_level = mme.get("risk_level", "unknown")

                risk_css = {
                    "high": "danger-high",
                    "increased": "danger-moderate",
                    "normal": "danger-low",
                }.get(risk_level, "")

                col1, col2, col3 = st.columns(3)
                with col1:
                    mme_display = f"{daily_mme:.1f}" if daily_mme is not None else "N/A"
                    _metric_card("Daily MME", mme_display, risk_css)
                with col2:
                    _metric_card(
                        "Risk Level",
                        risk_level.upper() if risk_level != "unknown" else "Unknown",
                        risk_css,
                    )
                with col3:
                    factor = mme.get("mme_factor_used")
                    _metric_card("MME Factor", f"{factor}" if factor else "N/A")

                lethal = result.get("lethal_dose_comparison")
                if lethal:
                    st.markdown("")
                    pct = lethal["daily_dose_as_pct_of_lethal"]
                    ld_mg = lethal["estimated_lethal_dose_mg"]

                    bar_color = "#ef4444" if pct > 50 else "#f59e0b" if pct > 20 else "#22c55e"
                    bar_width = min(pct, 100)

                    st.markdown(
                        f"**Lethal Dose Proximity:** {pct:.1f}% of estimated lethal dose "
                        f"({ld_mg:.0f} mg for a 70 kg adult)"
                    )
                    st.markdown(
                        f'<div style="background:#1b2838; border-radius:8px; height:24px; '
                        f'border:1px solid #2d4a5e; overflow:hidden;">'
                        f'<div style="background:{bar_color}; width:{bar_width}%; height:100%; '
                        f'border-radius:8px 0 0 8px; transition:width 0.5s;"></div></div>',
                        unsafe_allow_html=True,
                    )

                risk_factors = result.get("risk_factors", [])
                if risk_factors:
                    st.markdown("")
                    for rf in risk_factors:
                        if "HIGH RISK" in rf or "Extreme" in rf or "BOXED" in rf:
                            st.error(rf)
                        else:
                            st.warning(rf)

                recommendation = result.get("recommendation", "")
                if recommendation:
                    if recommendation.startswith("HIGH RISK"):
                        st.error(f"**Recommendation:** {recommendation}")
                    elif recommendation.startswith("CAUTION"):
                        st.warning(f"**Recommendation:** {recommendation}")
                    else:
                        st.success(f"**Recommendation:** {recommendation}")

                st.caption(
                    "CDC recommends avoiding doses >= 90 MME/day or carefully "
                    "justifying the decision to titrate above 50 MME/day."
                )

    # ------------------------------------------------------------------
    # Panel B: Danger Comparator
    # ------------------------------------------------------------------
    with tab2:
        st.markdown("<h2 class='section-header'>Danger Comparator</h2>",
                    unsafe_allow_html=True)
        st.markdown(
            "Compare the danger profiles of two opioid ingredients side by side "
            "with receptor affinity, potency, lethality, and therapeutic index."
        )

        col_a, col_b = st.columns(2)
        with col_a:
            drug_a = st.selectbox(
                "Drug A",
                ingredients,
                index=ingredients.index("morphine") if "morphine" in ingredients else 0,
                format_func=str.title,
                key="cmp_a",
            )
        with col_b:
            default_b = ingredients.index("fentanyl") if "fentanyl" in ingredients else 1
            drug_b = st.selectbox(
                "Drug B",
                ingredients,
                index=default_b,
                format_func=str.title,
                key="cmp_b",
            )

        if drug_a == drug_b:
            st.info("Select two different drugs to compare.")
        else:
            ip = pharmacology.get("ingredient_pharmacology", {})
            p_a = ip.get(drug_a, {})
            p_b = ip.get(drug_b, {})

            col1, col2 = st.columns(2)

            for col, name, p in [(col1, drug_a, p_a), (col2, drug_b, p_b)]:
                with col:
                    st.markdown(f"### {name.title()}")

                    danger = p.get("danger_level", "Unknown")
                    css = ("danger-high" if danger in ("Extreme", "Very High", "High")
                           else "danger-moderate" if danger == "Moderate" else "danger-low")
                    _metric_card("Danger Level", danger, css)

                    potency = p.get("potency_vs_morphine")
                    pot_css = "danger-high" if potency and potency > 10 else ""
                    _metric_card("Potency vs Morphine",
                                 f"{potency:.2f}x" if potency else "N/A", pot_css)

                    mu_ki = p.get("receptor_affinities", {}).get("mu", {}).get("ki_nM")
                    _metric_card("Mu Receptor Ki", f"{mu_ki} nM" if mu_ki else "N/A")

                    leth = p.get("estimated_human_lethal_dose_mg")
                    leth_css = "danger-high" if leth and leth < 100 else ""
                    _metric_card("Est. Lethal Dose (70kg)",
                                 f"{leth:.0f} mg" if leth else "Unknown", leth_css)

                    ti = p.get("therapeutic_index")
                    ti_css = "danger-high" if ti and ti < 10 else ""
                    _metric_card("Therapeutic Index",
                                 f"{ti:.1f}" if ti else "N/A", ti_css)

            st.divider()

            potency_a = p_a.get("potency_vs_morphine") or 0
            potency_b = p_b.get("potency_vs_morphine") or 0
            if potency_a and potency_b:
                if potency_a > potency_b:
                    ratio = potency_a / potency_b
                    st.markdown(
                        f"**{drug_a.title()}** is approximately **{ratio:.1f}x more potent** "
                        f"than {drug_b.title()} at the mu opioid receptor."
                    )
                elif potency_b > potency_a:
                    ratio = potency_b / potency_a
                    st.markdown(
                        f"**{drug_b.title()}** is approximately **{ratio:.1f}x more potent** "
                        f"than {drug_a.title()} at the mu opioid receptor."
                    )
                else:
                    st.markdown("Both drugs have similar potency at the mu receptor.")

    # ------------------------------------------------------------------
    # Panel C: Quick Intelligence Brief
    # ------------------------------------------------------------------
    with tab3:
        st.markdown("<h2 class='section-header'>Intelligence Brief</h2>",
                    unsafe_allow_html=True)
        st.markdown(
            "Generate a comprehensive opioid intelligence brief combining pharmacology, "
            "safety data, FAERS signals, and NLP-mined label warnings."
        )

        brief_drug = st.selectbox(
            "Select an opioid ingredient",
            ingredients,
            format_func=str.title,
            key="brief_drug",
        )

        ing_data = pharmacology.get("ingredient_pharmacology", {}).get(brief_drug, {})
        rxcui = ing_data.get("rxcui_ingredient", "")

        if rxcui:
            brief_text = watchdog.format_brief_text(rxcui)
            st.markdown(
                f'<div style="background:#1b2838; border:1px solid #2d4a5e; '
                f'border-radius:10px; padding:1.5rem; margin:1rem 0;">'
                f'{_md_to_html(brief_text)}</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Why is this an opioid?"):
                why = watchdog.answer_why_opioid(brief_drug)
                st.markdown(why)

            with st.expander("FAERS Signal Summary"):
                sig_text = watchdog.get_signals_summary(rxcui)
                st.markdown(sig_text)

            with st.expander("Label Warnings (NLP)"):
                label_text = watchdog.get_label_warnings(rxcui)
                st.markdown(label_text)
        else:
            st.info(f"No RxCUI found for {brief_drug.title()}. Intelligence brief unavailable.")


def _md_to_html(text: str) -> str:
    """Minimal markdown-to-HTML for the brief container."""
    import re
    lines = text.split("\n")
    out = []
    for line in lines:
        line = line.rstrip()
        if line.startswith("# "):
            out.append(f"<h3 style='color:#5eead4; margin:0 0 0.3rem 0;'>{line[2:]}</h3>")
        elif line.startswith("## "):
            out.append(f"<h4 style='color:#94a3b8; margin:1rem 0 0.3rem 0;'>{line[3:]}</h4>")
        elif line.startswith("  - "):
            out.append(f"<div style='margin-left:1rem; color:#e0e6ed;'>&bull; {line[4:]}</div>")
        elif line == "":
            out.append("<br/>")
        else:
            styled = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            out.append(f"<div style='color:#e0e6ed;'>{styled}</div>")
    return "\n".join(out)
