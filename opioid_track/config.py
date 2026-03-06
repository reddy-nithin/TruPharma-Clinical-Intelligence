"""
Opioid Track — Central Configuration
=====================================
All paths, API endpoints, and constants for the opioid track.
"""

# Base paths
OPIOID_DATA_DIR = "opioid_track/data"

# Output file paths
RXCLASS_OUTPUT = f"{OPIOID_DATA_DIR}/rxclass_opioid_enumeration.json"
NDC_LOOKUP_OUTPUT = f"{OPIOID_DATA_DIR}/ndc_opioid_lookup.json"
MME_REFERENCE_OUTPUT = f"{OPIOID_DATA_DIR}/mme_reference.json"
FAERS_QUERIES_OUTPUT = f"{OPIOID_DATA_DIR}/faers_opioid_queries.json"
REGISTRY_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_registry.json"

# === REPRODUCIBILITY: Raw data from pinned GitHub repos ===
# ripl-org/historical-ndc — Pre-classified NDC opioid lookup table (1998–2018)
# Published: JAMIA 2020 | License: MIT
RIPL_NDC_CSV_URL = "https://raw.githubusercontent.com/ripl-org/historical-ndc/master/output/ndc-opioids.csv"
RIPL_NDC_CSV_LOCAL = f"{OPIOID_DATA_DIR}/raw/ndc-opioids.csv"

# jbadger3/ml_4_pheno_ooe — RxCUI→MME mapping (peer-reviewed ML phenotyping paper)
# License: MIT
JBADGER_MME_JSON_URL = "https://raw.githubusercontent.com/jbadger3/ml_4_pheno_ooe/master/supporting_files/mme_OMOP.json"
JBADGER_MME_JSON_LOCAL = f"{OPIOID_DATA_DIR}/raw/rxcui_mme_mapping.json"

# API base URLs (all free, no auth required)
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"
OPENFDA_BASE = "https://api.fda.gov/drug"
DAILYMED_BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

# Rate limiting
RXNAV_DELAY_SECONDS = 0.05    # 20 req/sec max
OPENFDA_DELAY_SECONDS = 0.25  # ~4 req/sec to be safe

# Opioid ATC sub-classes for categorization
ATC_OPIOID_CLASSES = {
    "N02A": "Opioids (parent class)",
    "N02AA": "Natural opium alkaloids",
    "N02AB": "Phenylpiperidine derivatives",
    "N02AC": "Diphenylpropylamine derivatives",
    "N02AD": "Benzomorphan derivatives",
    "N02AE": "Oripavine derivatives",
    "N02AF": "Morphinan derivatives",
    "N02AG": "Opioids + antispasmodics",
    "N02AJ": "Opioids + non-opioid analgesics",
    "N02AX": "Other opioids",
    "N07BC": "Drugs used in opioid dependence",
}

# ATC code to opioid category mapping
ATC_TO_CATEGORY = {
    "N02AA": "natural/semi-synthetic",
    "N02AB": "synthetic",
    "N02AC": "synthetic",
    "N02AD": "synthetic",
    "N02AE": "semi-synthetic",
    "N02AF": "semi-synthetic",
    "N02AG": "combination",
    "N02AJ": "combination",
    "N02AX": "synthetic",
    "N07BC": "treatment/recovery",
}

# MED-RT concept IDs for opioid mechanisms of action
# NOTE: These are the actual MED-RT MOA class IDs (discovered via API exploration).
# The rela parameter must be "has_moa" (lowercase).
MEDRT_OPIOID_CONCEPTS = {
    "N0000191866": "Opioid mu-Receptor Agonists",
    "N0000000154": "Opioid Antagonists",
    "N0000175685": "Partial Opioid Agonists",
}

# FDA Established Pharmacologic Classes
# NOTE: EPC classes use numeric concept IDs with relaSource=FDASPL and rela=has_EPC.
FDA_EPC_OPIOID = {
    "N0000175690": "Opioid Agonist [EPC]",
    "N0000175691": "Opioid Antagonist [EPC]",
    "N0000175692": "Opioid Partial Agonist [EPC]",
    "N0000175688": "Opioid Agonist-Antagonist [EPC]",
    "N0000175693": "Opioid Agonist-Antagonist [EPC]",
}

# DEA schedules to check
DEA_SCHEDULES = ["CII", "CIII", "CIV", "CV"]

# CDC MME conversion factors (per mg oral, unless noted)
# These are the fallback if jbadger3/ml_4_pheno_ooe JSON download fails
CDC_MME_FACTORS = {
    "codeine": 0.15,
    "tramadol": 0.2,
    "tapentadol": 0.4,
    "meperidine": 0.4,
    "morphine": 1.0,
    "oxycodone": 1.5,
    "hydrocodone": 1.0,
    "hydromorphone": 5.0,
    "oxymorphone": 3.0,
    "fentanyl": 2.4,          # transdermal mcg/hr to MME
    "buprenorphine": 12.6,
    "levorphanol": 11.0,
    "pentazocine": 0.37,
    "butorphanol": 7.0,
}

# Methadone has dose-dependent conversion
METHADONE_MME_TIERS = [
    (20, 4.7),    # ≤20 mg/day → factor 4.7
    (40, 8.0),    # 21-40 mg/day → factor 8.0
    (60, 10.0),   # 41-60 mg/day → factor 10.0
    (80, 12.0),   # 61-80 mg/day → factor 12.0
]

# Key MedDRA preferred terms for opioid safety monitoring
OPIOID_SAFETY_TERMS = [
    "Respiratory depression",
    "Respiratory failure",
    "Respiratory arrest",
    "Drug dependence",
    "Drug abuse",
    "Substance abuse",
    "Overdose",
    "Intentional overdose",
    "Accidental overdose",
    "Drug toxicity",
    "Death",
    "Completed suicide",
    "Neonatal abstinence syndrome",
    "Neonatal opioid withdrawal syndrome",
    "Withdrawal syndrome",
    "Drug withdrawal syndrome",
    "Somnolence",
    "Coma",
    "Loss of consciousness",
    "Constipation",
    "Serotonin syndrome",
]

# Minimum known opioids for validation
MUST_INCLUDE_OPIOIDS = [
    "morphine", "codeine", "oxycodone", "hydrocodone",
    "fentanyl", "methadone", "buprenorphine", "tramadol",
    "tapentadol", "meperidine", "hydromorphone", "oxymorphone",
    "naloxone", "naltrexone",
]

# === TIER 1.5 ADDITIONS ===

# Real-time NDC Sync
REALTIME_NDC_OUTPUT = f"{OPIOID_DATA_DIR}/realtime_ndc_opioids.json"
OPENFDA_NDC_QUERY_OPIOID = 'pharm_class:"opioid"'
OPENFDA_RECENT_YEAR_START = "20190101"
OPENFDA_RECENT_YEAR_END = "20251231"

