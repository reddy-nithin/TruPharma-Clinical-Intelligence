"""
TruPharma Opioid Dashboard — Accessibility & Plain-English Layer
================================================================
Four-tier system for making the dashboard understandable to a general
audience while preserving all clinical depth for expert users.

Tier 1 — Inline tooltips    : tt() + WIDGET_HELP
Tier 2 — Chart captions     : chart_caption() + CHART_CAPTIONS
Tier 3 — Section banners    : section_banner() + BANNERS
Tier 4 — Sidebar glossary   : render_sidebar_glossary() + GLOSSARY
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Tier 1 — Inline tooltip helper
# ---------------------------------------------------------------------------

def tt(term: str, definition: str) -> str:
    """
    Returns an HTML span with a CSS hover tooltip.
    Use inside any st.markdown(..., unsafe_allow_html=True) call.

    Example:
        st.markdown(f"Value: {tt('MME', GLOSSARY['MME (Morphine Milligram Equivalent)'])}", unsafe_allow_html=True)
    """
    return (
        f"<span class='tp-tooltip-wrap'>"
        f"<span class='tp-tooltip-term'>{term}</span>"
        f"<span class='tp-tooltip-box'>{definition}</span>"
        f"</span>"
    )


WIDGET_HELP: dict[str, str] = {
    "drug_search": (
        "Search by brand name, generic drug name, active ingredient, or RxCUI "
        "(a unique drug ID number assigned by the National Library of Medicine)."
    ),
    "drug_select": (
        "Select a specific drug product to explore its full safety profile, "
        "pharmacology, warning labels, and FDA adverse event signals."
    ),
    "dose_drug": (
        "Choose the active opioid ingredient — the chemical that produces the "
        "opioid effect, regardless of brand name or formulation."
    ),
    "dose_mg": (
        "Enter the total amount of this drug taken in a single day, in milligrams (mg). "
        "For reference: a typical starting morphine dose is 10–30 mg/day."
    ),
    "metric_select": (
        "Choose which measurement to display on the map. "
        "Risk Score combines prescribing, death, and claims data into one 0–1 number. "
        "Higher = greater opioid burden."
    ),
    "tier_filter": (
        "Risk Tier (High/Medium/Low) is derived from the composite Risk Score. "
        "High = top 30% nationally. This is relative — even 'Low' counties may "
        "have significant opioid challenges in absolute terms."
    ),
    "risk_range_slider": (
        "Risk Score is a 0–1 composite index. Scores above 0.4 indicate multiple "
        "risk factors converging (high prescribing + high deaths + high claims). "
        "Most counties fall between 0.05 and 0.35."
    ),
    "signal_drug": (
        "Select a drug to view its adverse event reports from FAERS — the FDA's "
        "voluntary reporting database. Reports are submitted by doctors, patients, "
        "and drug companies when they suspect a drug caused a reaction."
    ),
    "show_consensus": (
        "A consensus signal means all 3 statistical detection methods (PRR, ROR, EBGM) "
        "independently flagged this drug-reaction pair as unusually common. "
        "This is the strongest signal level — requiring agreement across methods "
        "significantly reduces false positives."
    ),
    "sort_signals": (
        "Methods Flagging: how many of the 3 statistical algorithms detected this signal. "
        "Report Count: raw number of FDA adverse event reports filed for this pair. "
        "More reports = more data, but not necessarily a stronger signal."
    ),
    "completeness": (
        "Some counties have partial data due to rural population suppression (CDC "
        "withholds death rates when counts are below 10, to protect privacy). "
        "Filtering to 'Complete' ensures fair comparison across counties."
    ),
    "cmp_a": (
        "Select the first drug to compare. Morphine is set as the default because "
        "it is the international reference standard — all opioid potencies are "
        "measured relative to morphine."
    ),
    "cmp_b": (
        "Select the second drug. Fentanyl is shown by default as a high-contrast "
        "example — it is 50–100x more potent than morphine, which is why accidental "
        "exposure is so dangerous."
    ),
}


# ---------------------------------------------------------------------------
# Tier 2 — Chart interpretation captions
# ---------------------------------------------------------------------------

def chart_caption(text: str):
    """Renders a plain-English interpretation callout below a chart."""
    st.markdown(
        f"<div class='tp-chart-caption'>"
        f"<span class='tp-chart-caption-icon'>&#x1F4CA;</span> {text}"
        f"</div>",
        unsafe_allow_html=True,
    )


CHART_CAPTIONS: dict[str, str] = {
    "receptor_bar": (
        "This chart shows how strongly the drug binds to each opioid receptor in the "
        "brain and body. Lower bars (lower Ki nM) mean tighter binding — so a drug with "
        "a Ki of 0.1 nM at the mu receptor is about 10x more potent than one with 1 nM. "
        "The mu receptor (&#956;) is the primary target for both pain relief and the "
        "dangerous respiratory depression that causes overdose death."
    ),
    "ld50_note": (
        "LD50 is the dose that killed 50% of laboratory animals in controlled studies. "
        "These figures are used as a relative toxicity scale — they are not direct human "
        "measurements. A lower LD50 means a smaller dose is potentially lethal. "
        "The 70 kg adult lethal dose estimate is extrapolated from these animal values."
    ),
    "treemap": (
        "Each box represents an opioid drug or ingredient, grouped by chemical family "
        "(natural, semi-synthetic, synthetic, etc.). Box size reflects how many FDA "
        "adverse event reports exist for that ingredient in the FAERS database — larger "
        "boxes have generated more safety reports, indicating either higher use or more "
        "reported harms."
    ),
    "potency_bar": (
        "All drugs are compared to morphine, the international reference standard "
        "(the dashed vertical line at 1&#x00D7;). Fentanyl at 100&#x00D7; means a dose "
        "100 times smaller than morphine produces the same effect — this is why a "
        "few grains of illicit fentanyl can be fatal. Red bars have the strongest "
        "receptor binding; teal bars have relatively weaker binding."
    ),
    "schedule_donut": (
        "The DEA assigns controlled substances a schedule from CII (highest restriction "
        "— high abuse potential, accepted medical use) to CV (lowest restriction). "
        "Most opioid pain medications are Schedule II. Buprenorphine formulations for "
        "addiction treatment are often Schedule III. The schedule determines how a drug "
        "can be prescribed, stored, and tracked."
    ),
    "danger_matrix": (
        "This chart plots two independent safety dimensions simultaneously. Right = more "
        "potent than morphine. Up = wider safety margin between an effective dose and a "
        "dangerous one (Therapeutic Index). Drugs in the <strong>bottom-right</strong> "
        "corner are the most dangerous: highly potent with almost no room for error. "
        "The dashed line at TI=10 marks a conventional clinical boundary — below it, "
        "even small dosing errors can be life-threatening."
    ),
    "faers_scatter": (
        "This chart crosses pharmacology data with real-world harm reports. Dots farther "
        "right are more potent opioids; dots higher up have generated more FDA adverse "
        "event reports. Bubble size scales with danger rank — larger bubbles are ranked "
        "as more dangerous. A drug in the top-right corner has both high potency and "
        "a large volume of reported harms."
    ),
    "three_waves": (
        "The opioid crisis unfolded in three overlapping waves: <strong>Wave 1</strong> "
        "(late 1990s) was driven by aggressive marketing of prescription opioids like "
        "OxyContin. <strong>Wave 2</strong> (around 2010) saw a heroin surge as pill "
        "access tightened — heroin was cheaper and more available. "
        "<strong>Wave 3</strong> (2013&#x2013;present) is dominated by illicitly "
        "manufactured fentanyl and analogues, which now cause the majority of the "
        "~80,000 annual US opioid overdose deaths."
    ),
    "choropleth": (
        "Darker colors indicate higher values for the selected metric. The map is "
        "aggregated at the state level (county-level data is in the County Detail "
        "section below). The Risk Score is a composite measure — no single metric "
        "tells the full story; states with moderate death rates may still have "
        "very high prescribing rates."
    ),
    "state_bar": (
        "States are ranked by the currently selected metric. Red bars are in the top "
        "30% nationally, amber in the middle 30&#x2013;70%, teal in the lower third. "
        "This is a relative ranking — even 'low risk' (teal) states may have significant "
        "opioid problems; they are simply below the national median for this metric."
    ),
    "overdose_timeline": (
        "This chart tracks national overdose deaths over time. The red line shows "
        "opioid-specific deaths climbing sharply after 2013 — primarily due to illicitly "
        "manufactured fentanyl entering the drug supply. The gap between total overdoses "
        "(white line) and opioid-specific deaths (red line) represents deaths from other "
        "substances like stimulants."
    ),
    "faers_heatmap": (
        "Each cell is a drug-reaction pair. Color shows how many statistical detection "
        "methods independently flagged it as a safety signal: dark teal = 1 method, "
        "amber = 2 methods, red = all 3 (consensus — the strongest classification). "
        "Empty/dark cells mean that combination was not flagged or not present in FAERS. "
        "This is not proof the drug causes the reaction — it flags patterns worth "
        "investigating."
    ),
    "lethal_bar": (
        "This bar shows your entered daily dose as a percentage of the estimated lethal "
        "dose for a 70 kg adult. This is not a clinical prediction — individual responses "
        "vary significantly based on tolerance, body composition, and concurrent medications. "
        "It illustrates why precise dosing matters with narrow therapeutic index drugs."
    ),
}


# ---------------------------------------------------------------------------
# Tier 3 — Section context banners
# ---------------------------------------------------------------------------

def section_banner(title: str, body: str, expanded: bool = False):
    """
    A collapsible 'What is X?' context banner. Collapsed by default so
    expert users can ignore it; clearly visible and clickable for novices.
    """
    with st.expander(f"What is \"{title}\"?", expanded=expanded):
        st.markdown(
            f"<div class='tp-section-banner'>{body}</div>",
            unsafe_allow_html=True,
        )


BANNERS: dict[str, str] = {
    "drug_identity": (
        "This section identifies the specific drug product you selected. "
        "<strong>RxCUI</strong> is a unique numerical code from the National Library "
        "of Medicine's RxNorm system — it uniquely identifies this drug formulation. "
        "<strong>Schedule</strong> is the DEA's control classification: CII drugs have "
        "strict prescribing rules because of high misuse potential, while CIV/CV drugs "
        "have lower restriction levels. <strong>Category</strong> refers to the chemical "
        "family the opioid belongs to (natural, semi-synthetic, synthetic, or combination)."
    ),
    "pharmacology": (
        "Pharmacology describes how a drug works at the molecular level. "
        "<strong>Receptor Affinity</strong> measures how tightly the drug binds to "
        "opioid receptors in the brain — lower Ki (nM) values mean stronger binding "
        "and more potent effects at smaller doses. <strong>Potency vs Morphine</strong> "
        "tells you how large a dose is needed compared to the reference drug morphine "
        "— fentanyl at 100&#x00D7; means you need 1/100th the dose for the same effect. "
        "<strong>Half-Life</strong> is how long the drug stays active in the body — "
        "methadone's unusually long half-life (24&#x2013;36 hours) makes it easy to "
        "accidentally accumulate toxic levels. <strong>Molecular Weight</strong> is the "
        "atomic mass of the compound — larger molecules tend to absorb and distribute "
        "differently in the body."
    ),
    "safety_profile": (
        "This section quantifies the danger of the drug using standardized measures. "
        "<strong>MME (Morphine Milligram Equivalent)</strong> is a conversion factor "
        "that lets clinicians compare doses across different opioids on one scale — "
        "the CDC flags daily prescribing above 90 MME as high risk. "
        "<strong>Therapeutic Index (TI)</strong> is the ratio between the harmful dose "
        "and the therapeutic dose: TI&nbsp;=&nbsp;5 means the toxic dose is only 5&#x00D7; "
        "the effective dose, leaving very little margin for error. "
        "<strong>LD50</strong> is a laboratory measure from animal studies of the dose "
        "that would be lethal to half of test subjects — it gives a rough scale of how "
        "dangerous an overdose could be. <strong>Danger Level</strong> is an expert-assigned "
        "classification based on potency, TI, LD50, and clinical history."
    ),
    "faers_signals": (
        "<strong>FAERS</strong> (FDA Adverse Event Reporting System) is a database where "
        "healthcare providers, patients, and drug companies voluntarily report suspected "
        "adverse drug reactions. A <strong>signal</strong> is a statistical flag suggesting "
        "a drug may cause a specific reaction more often than expected — it is not proof "
        "of causation. "
        "<strong>PRR</strong> (Proportional Reporting Ratio), <strong>ROR</strong> "
        "(Reporting Odds Ratio), and <strong>EBGM</strong> (Empirical Bayes Geometric Mean) "
        "are three independent mathematical methods for detecting signals in FAERS. "
        "When all three agree, it is called a <strong>consensus signal</strong> — the "
        "strongest level of concern, significantly less likely to be a false positive."
    ),
    "label_highlights": (
        "Drug labels (package inserts) are official FDA-approved documents listing all "
        "known warnings, dosing instructions, and drug interactions. This section uses "
        "<strong>Natural Language Processing (NLP)</strong> to automatically extract "
        "the most critical information from those documents. "
        "A <strong>Boxed Warning</strong> is the FDA's most severe warning — it means "
        "the drug has known risks serious enough to potentially cause death or severe "
        "injury if misused. All long-acting opioids carry one. "
        "<strong>REMS</strong> (Risk Evaluation and Mitigation Strategy) is a special "
        "FDA-required safety program with mandatory prescriber training and patient "
        "enrollment steps before dispensing. "
        "<strong>CYP Interactions</strong> refer to liver enzymes that metabolize drugs "
        "— when two drugs compete for the same enzyme, levels of both can rise to "
        "dangerous concentrations."
    ),
    "landscape_classification": (
        "Opioids are classified into chemical families based on their origin and structure. "
        "<strong>Natural opioids</strong> (morphine, codeine) come directly from the "
        "opium poppy plant. <strong>Semi-synthetic opioids</strong> (oxycodone, hydrocodone) "
        "are chemically modified versions of natural opioids. <strong>Synthetic opioids</strong> "
        "(fentanyl, methadone) are entirely manufactured in a lab. "
        "<strong>Combination products</strong> pair an opioid with another drug "
        "(often acetaminophen/Tylenol). Classification affects pharmacology, abuse potential, "
        "and regulatory status."
    ),
    "danger_matrix": (
        "This chart plots two independent safety dimensions at once. The <strong>horizontal "
        "axis (potency)</strong> tells you how much drug is needed to have an effect — "
        "more potent drugs require tiny doses, making accidental overdose easier. "
        "The <strong>vertical axis (Therapeutic Index)</strong> tells you how much margin "
        "exists between an effective dose and a harmful one. "
        "Drugs in the bottom-right quadrant are the most dangerous: highly potent AND "
        "almost no safety margin. The dashed line at TI&nbsp;=&nbsp;10 marks a "
        "conventional clinical boundary — below it, even small dosing errors can be "
        "life-threatening."
    ),
    "three_waves": (
        "Public health experts describe the US opioid crisis as three distinct but "
        "overlapping waves. <strong>Wave 1</strong> (late 1990s) began when pharmaceutical "
        "companies aggressively marketed OxyContin and similar drugs, downplaying addiction "
        "risk. <strong>Wave 2</strong> (&#x2248;2010) saw a heroin surge as prescription "
        "opioid access tightened — many people already dependent on pills switched to "
        "heroin, which was cheaper and more available. <strong>Wave 3</strong> "
        "(2013&#x2013;present) is dominated by illicitly manufactured fentanyl and "
        "analogues — synthetic opioids are now found in counterfeit pills, heroin, "
        "and cocaine, and now cause the majority of the roughly 80,000 annual US "
        "opioid overdose deaths."
    ),
    "geo_map": (
        "This map shows the United States colored by your selected metric, aggregated "
        "to the state level. Darker = higher on the selected metric. "
        "<strong>Risk Score</strong> (0&#x2013;1 scale) combines prescribing rates, "
        "overdose death rates, and Medicaid claims — it is a weighted composite, not "
        "a single measurement. <strong>Prescribing Rate</strong> is opioid prescriptions "
        "filled per 100 Medicare Part D beneficiaries. <strong>Death Rate</strong> is "
        "opioid overdose deaths per 100,000 people (from CDC WONDER). "
        "<strong>Claims Per Capita</strong> reflects Medicaid opioid drug utilization. "
        "No single metric tells the full story — compare them to identify states where "
        "multiple risk factors converge."
    ),
    "geo_county": (
        "County data is joined from three federal sources: CMS Medicare prescribing data, "
        "CDC WONDER mortality data, and Medicaid drug claims. Many counties show 'N/A' "
        "because the CDC <strong>suppresses death rate data</strong> when counts are below "
        "10 cases, to protect patient privacy — this disproportionately affects rural "
        "counties with small populations. "
        "The <strong>Risk Tier</strong> (High/Medium/Low) is derived from the composite "
        "Risk Score: High = top 30% nationally, Medium = middle 40%, Low = bottom 30%. "
        "These are relative rankings within the US county dataset."
    ),
    "signal_detection": (
        "Pharmacovigilance is the science of detecting, assessing, and preventing "
        "drug-related side effects after a drug is on the market. This page uses "
        "<strong>FAERS</strong> (FDA Adverse Event Reporting System) data and applies "
        "three independent mathematical algorithms to identify unusual drug-reaction "
        "patterns. <strong>PRR</strong> (Proportional Reporting Ratio) and "
        "<strong>ROR</strong> (Reporting Odds Ratio) compare how often a reaction "
        "appears with a specific drug versus all other drugs. "
        "<strong>EBGM</strong> (Empirical Bayes Geometric Mean) uses Bayesian "
        "statistics to estimate true signal strength. When all three flag the same "
        "pair, we call it a <strong>consensus signal</strong> — this does not prove "
        "the drug causes the reaction, but enough reports have accumulated to warrant "
        "regulatory attention."
    ),
    "signal_detail": (
        "Each statistical method has its own threshold for declaring a signal. "
        "<strong>PRR &gt; 2 with &#967;&#178; &gt; 4</strong> is the UK MHRA standard. "
        "<strong>ROR &gt; 2 with the lower bound of the 95% confidence interval also "
        "above 1</strong> is the European EMA standard — the 95% CI tells you how "
        "confident we are in the estimate. "
        "<strong>EBGM &gt; 2 with EB05 &gt; 2</strong> is the WHO/FDA Bayesian "
        "standard. Requiring all three methods to agree simultaneously reduces false "
        "positives significantly compared to any single method alone."
    ),
    "dose_calc": (
        "This tool converts your entered dose into <strong>MME (Morphine Milligram "
        "Equivalents)</strong>, a standardized unit that lets us compare doses across "
        "different opioids on one scale. The CDC's 2022 Clinical Practice Guideline "
        "recommends clinicians avoid prescribing above 50 MME/day without strong "
        "justification, and avoid exceeding 90 MME/day entirely. "
        "The <strong>lethal dose proximity bar</strong> shows your entered dose as a "
        "percentage of the estimated lethal dose for a 70 kg adult — extrapolated from "
        "animal LD50 data and pharmacological models. This is not a clinical prediction; "
        "individual responses vary greatly based on tolerance, weight, and other drugs "
        "being taken simultaneously."
    ),
    "comparator": (
        "This side-by-side view compares two opioids on the dimensions that determine "
        "danger. <strong>Potency vs Morphine</strong>: how large a dose is needed "
        "relative to morphine — higher potency = tinier effective dose = more dangerous "
        "if accidentally exposed. <strong>Mu Receptor Ki</strong>: binding strength "
        "at the primary opioid receptor — lower nM value = tighter binding = stronger "
        "effect per molecule. <strong>Therapeutic Index</strong>: the safety margin "
        "between effective and toxic dose — below 10 is considered narrow. "
        "<strong>Estimated Lethal Dose</strong>: extrapolated from LD50 animal data "
        "for a 70 kg adult."
    ),
    "brief": (
        "The Intelligence Brief automatically aggregates data from three pipelines: "
        "the <strong>pharmacology database</strong> (receptor affinities, potency, LD50), "
        "the <strong>NLP-analyzed FDA drug label</strong> (warnings, dosing limits, "
        "drug interactions extracted from official prescribing information), and the "
        "<strong>FAERS signal detection results</strong> (which adverse events are "
        "statistically flagged). Use the expandable sections below the brief to explore "
        "each data source in more detail."
    ),
}


# ---------------------------------------------------------------------------
# Tier 4 — Sidebar glossary
# ---------------------------------------------------------------------------

GLOSSARY: dict[str, str] = {
    "MME (Morphine Milligram Equivalent)": (
        "A standard unit for comparing opioid doses across different drugs. Each drug "
        "has a conversion factor: 10 mg oxycodone = 15 MME, 0.1 mg fentanyl (patch) "
        "= 25 MME. The CDC flags daily prescribing above 90 MME/day as high-risk."
    ),
    "Therapeutic Index (TI)": (
        "The ratio of the toxic dose to the therapeutic (effective) dose. TI = 5 means "
        "the harmful dose is only 5\u00d7 the effective dose. Lower TI = less room for "
        "error. Drugs with TI < 10 are called 'narrow therapeutic index' drugs."
    ),
    "LD50": (
        "The dose that killed 50% of laboratory animals in controlled studies. Used as "
        "a relative toxicity measure — not measured directly in humans. Expressed as "
        "mg per kg of body weight. Lower LD50 = more toxic (smaller dose is lethal)."
    ),
    "Ki (nM) — Binding Affinity": (
        "Measures how tightly a drug binds to a receptor. Ki is the 'inhibition constant' "
        "in nanomolar (nM) units. Lower Ki = tighter binding = more potent effect. "
        "Fentanyl's mu receptor Ki of ~0.4 nM is far stronger than morphine's ~2 nM."
    ),
    "Mu (\u03bc) Receptor": (
        "The primary opioid receptor responsible for pain relief, euphoria, and "
        "respiratory depression. Most opioids mainly target this receptor. "
        "Overstimulation causes the breathing suppression that leads to overdose death."
    ),
    "FAERS": (
        "FDA Adverse Event Reporting System — a public database where healthcare "
        "providers, patients, and drug companies voluntarily submit reports of suspected "
        "adverse drug reactions. It is not a clinical trial; reports suggest associations, "
        "not proven causation."
    ),
    "PRR (Proportional Reporting Ratio)": (
        "A signal detection statistic. PRR > 2 with \u03c7\u00b2 > 4 indicates a "
        "drug-reaction pair appears disproportionately often vs all other drugs in FAERS. "
        "Used by the UK Medicines & Healthcare products Regulatory Agency (MHRA)."
    ),
    "ROR (Reporting Odds Ratio)": (
        "Similar to PRR but uses odds ratio methodology. ROR > 2 with the lower 95% "
        "confidence interval also above 1 indicates a signal. Used by the European "
        "Medicines Agency (EMA). More conservative than PRR for rare reactions."
    ),
    "EBGM (Empirical Bayes Geometric Mean)": (
        "A Bayesian statistical measure used by the FDA and WHO to detect safety signals. "
        "EBGM > 2 (and EB05 > 2) indicates a signal. More robust than PRR/ROR for drugs "
        "with few reports because it adjusts estimates toward the population average."
    ),
    "EB05": (
        "The lower 5th percentile of the Bayesian EBGM confidence interval. When "
        "EB05 > 2, we are 95% confident the true signal is above 2 — a conservative "
        "threshold that minimizes false positives."
    ),
    "Consensus Signal": (
        "A drug-reaction pair flagged by all three detection methods (PRR, ROR, EBGM) "
        "simultaneously. This is the strongest signal classification — requiring multiple "
        "independent methods to agree substantially reduces false positives."
    ),
    "95% Confidence Interval (CI)": (
        "A range we are 95% sure contains the true value. If the 95% CI for ROR is "
        "[2.1, 4.8], the true ROR is likely between 2.1 and 4.8. When the lower bound "
        "exceeds a threshold (like 1 for ROR), the finding is statistically meaningful."
    ),
    "DEA Schedules (CII\u2013CV)": (
        "The DEA classifies controlled substances by abuse potential. CII = highest: "
        "high abuse potential, accepted medical use, severe dependence risk (most opioids). "
        "CIV/CV = lower restriction. Heroin = Schedule I (no accepted medical use)."
    ),
    "RxCUI": (
        "RxNorm Concept Unique Identifier — a standard numerical ID assigned by the "
        "National Library of Medicine to uniquely identify drugs, ingredients, and "
        "formulations. Used for interoperability across health systems and research."
    ),
    "Boxed Warning": (
        "The FDA's strongest safety warning, appearing in a black box at the top of "
        "the drug label. It means clinical evidence has identified a risk serious enough "
        "to potentially cause severe injury or death if misused. All long-acting opioids "
        "carry a boxed warning."
    ),
    "REMS (Risk Evaluation & Mitigation Strategy)": (
        "An FDA-required safety program for drugs with serious risks. REMS may require "
        "prescriber training, patient enrollment, and pharmacy certification before the "
        "drug can be dispensed. Extended-release and long-acting opioids require an "
        "opioid REMS."
    ),
    "CYP Interactions": (
        "Cytochrome P450 enzymes in the liver metabolize most drugs. When two drugs "
        "compete for the same CYP enzyme (e.g., CYP3A4), one can slow or speed the "
        "breakdown of the other, causing blood levels to rise dangerously or fall "
        "ineffectively. CYP3A4 and CYP2D6 are the most clinically important."
    ),
    "Potency vs Morphine": (
        "How much drug is needed compared to morphine (the international reference "
        "standard) to produce the same effect. Fentanyl at 100\u00d7 means 0.1 mg "
        "fentanyl = 10 mg morphine. Higher potency means dosing precision is critical."
    ),
    "Half-Life": (
        "The time for the body to eliminate half of a drug. A 4-hour half-life drug "
        "is mostly gone after 24 hours. Methadone's 24\u201336 hour half-life makes "
        "dosing dangerous — effects outlast patient awareness, leading to accumulation."
    ),
    "Naloxone (Narcan)": (
        "A medication that rapidly reverses opioid overdose by blocking opioid receptors. "
        "No effect without opioids present. Available without a prescription in all US "
        "states. Duration (30\u201390 min) may be shorter than long-acting opioids, "
        "requiring repeat doses."
    ),
    "SPL / DailyMed": (
        "Structured Product Labeling — the FDA's XML format for official drug labels "
        "(package inserts). DailyMed is the NIH database hosting all FDA-approved "
        "SPL documents. NLP in this dashboard extracted safety information from SPL files."
    ),
    "NLP (Natural Language Processing)": (
        "A branch of AI that reads and extracts structured information from text documents. "
        "Used here to automatically mine FDA drug label documents (written in clinical "
        "prose) for warnings, dosing limits, and drug interactions."
    ),
    "Risk Score": (
        "A composite 0\u20131 index per county combining prescribing rates, overdose "
        "death rates, and Medicaid claims per capita. Normalized relative to the national "
        "dataset. Identifies areas where multiple risk factors converge. Not a single "
        "measurement — a weighted combination."
    ),
    "Prescribing Rate": (
        "Number of opioid prescriptions filled per 100 Medicare Part D beneficiaries "
        "in a county. High rates may indicate overprescribing or high legitimate medical "
        "need — context is required to distinguish them."
    ),
    "Death Rate per 100K": (
        "Opioid overdose deaths per 100,000 population, from CDC WONDER mortality "
        "database. Many rural counties show 'N/A' because CDC suppresses counts below "
        "10 to protect patient privacy."
    ),
    "ICD-10 T-Codes": (
        "Cause-of-death codes on death certificates. T40.1 = heroin, T40.2 = "
        "natural/semi-synthetic opioids (oxycodone, hydrocodone), T40.3 = methadone, "
        "T40.4 = synthetic opioids (fentanyl). The three epidemic waves map to these "
        "codes over time."
    ),
    "The Three Waves": (
        "Wave 1 (late 1990s): prescription opioid overprescribing. Wave 2 (\u22482010): "
        "heroin surge as pill access tightened. Wave 3 (2013\u2013present): illicitly "
        "manufactured fentanyl and analogues — now present in counterfeit pills, "
        "heroin, and cocaine, causing ~80,000 annual opioid overdose deaths."
    ),
    "Opioid Category": (
        "The chemical family an opioid belongs to. Natural: from the poppy plant. "
        "Semi-synthetic: chemically modified natural opioids. Synthetic: entirely "
        "lab-made. Treatment/Recovery: buprenorphine and methadone used to treat "
        "opioid use disorder."
    ),
    "Buprenorphine": (
        "A partial opioid agonist used to treat opioid use disorder. Activates receptors "
        "just enough to prevent withdrawal without producing a full opioid high. "
        "Has a 'ceiling effect' that reduces overdose risk. Requires a prescription "
        "from a specially waivered provider."
    ),
    "Benzo Warning": (
        "A benzodiazepine (e.g., Xanax, Valium, Klonopin) interaction warning. "
        "Combining opioids with benzodiazepines causes additive respiratory depression "
        "— both drug classes slow breathing, and together they dramatically increase "
        "overdose risk. This combination is involved in ~30% of opioid overdose deaths."
    ),
}


def _glossary_html() -> str:
    items = []
    for term, definition in GLOSSARY.items():
        items.append(
            f"<div class='tp-glossary-item'>"
            f"<div class='tp-glossary-term'>{term}</div>"
            f"<div class='tp-glossary-def'>{definition}</div>"
            f"</div>"
        )
    return "<div class='tp-glossary'>" + "".join(items) + "</div>"


def render_sidebar_glossary():
    """Call from render_sidebar() in opioid_app.py after the data sources block."""
    with st.expander("Glossary \u2014 Key Terms"):
        st.markdown(_glossary_html(), unsafe_allow_html=True)
