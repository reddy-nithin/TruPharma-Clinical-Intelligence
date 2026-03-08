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

# === TIER 2 ADDITIONS ===

# CMS data
CMS_PRESCRIBING_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_prescribing.json"
CMS_GEO_URL = "https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-opioid-prescribing-rates/medicare-part-d-opioid-prescribing-rates-by-geography"
CMS_PROVIDER_DRUG_URL = "https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug"
MEDICAID_SDUD_BASE = "https://data.medicaid.gov/resource"

# CDC mortality data
CDC_MORTALITY_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_mortality.json"
CDC_VSRR_ENDPOINT = "https://data.cdc.gov/resource/xkb8-kh2a.json"
CDC_WONDER_BASE = "https://wonder.cdc.gov"
# alipphardt/cdc-wonder-api clone path (cloned during Step 4 setup)
CDC_WONDER_API_DIR = "opioid_track/vendor/cdc-wonder-api"
VSRR_OPIOID_INDICATORS = [
    "Opioids (T40.0-T40.4,T40.6)",
    "Natural & semi-synthetic opioids (T40.2)",
    "Methadone (T40.3)",
    "Synthetic opioids, excl. methadone (T40.4)",
    "Heroin (T40.1)",
]
ICD10_OPIOID_CODES = {
    "T40.0": "Opium",
    "T40.1": "Heroin",
    "T40.2": "Natural/semi-synthetic opioids",
    "T40.3": "Methadone",
    "T40.4": "Synthetic opioids (primarily fentanyl)",
    "T40.6": "Other/unspecified narcotics",
}

# =============================================================================
# CMS MEDICAID OPIOID (SUPPLY CHAIN PROXY) SETTINGS
# UUID for Medicaid Opioid Prescribing Rates - by Geography
# =============================================================================

CMS_MEDICAID_GEO_UUID = "c37ebe6d-f54f-4d7d-861f-fefe345554e6"
MEDICAID_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_supply_chain.json"
MEDICAID_DELAY_SECONDS = 0.5

# Signal detection (uses ChapatiDB/faerslib)
SIGNAL_RESULTS_OUTPUT = f"{OPIOID_DATA_DIR}/faers_signal_results.json"
SIGNAL_CACHE_FILE = f"{OPIOID_DATA_DIR}/faers_signal_cache.json"
# faerslib supports: "prr", "ror", "mgps" (EBGM-based)
SIGNAL_METHODS = ["prr", "ror", "mgps"]
SIGNAL_CONSENSUS_THRESHOLD = 2  # minimum methods that must flag for consensus signal

# Geographic profiles
GEO_PROFILES_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_geographic_profiles.json"
CENSUS_API_BASE = "https://api.census.gov/data"
CENSUS_API_KEY = "00ea40392d577c234f83e960a8ce07b5c0bab1b8"

# === TIER 3 ADDITIONS ===

# Pharmacology data
PHARMACOLOGY_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_pharmacology.json"
CHEMBL_DELAY_SECONDS = 0.1
CHEMBL_OPIOID_TARGETS = {
    "mu":    {"chembl_id": "CHEMBL233",     "gene": "OPRM1", "uniprot": "P35372", "gtopdb_id": 319},
    "kappa": {"chembl_id": "CHEMBL237",     "gene": "OPRK1", "uniprot": "P41145", "gtopdb_id": 320},
    "delta": {"chembl_id": "CHEMBL236",     "gene": "OPRD1", "uniprot": "P41143", "gtopdb_id": 321},
    "nop":   {"chembl_id": "CHEMBL2014868", "gene": "OPRL1", "uniprot": "P41146", "gtopdb_id": 322},
}
GTOPDB_API_BASE = "https://www.guidetopharmacology.org/services"
PUBCHEM_API_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Toxicology
TOXICOLOGY_SPECIES_PRIORITY = ["human", "rat", "mouse", "rabbit", "dog"]
TOXICOLOGY_ROUTE_PRIORITY = ["oral", "intravenous", "subcutaneous", "intraperitoneal", "inhalation"]

KM_SCALING = {
    "mouse": 3.0,
    "rat": 6.2,
    "rabbit": 12.0,
    "dog": 20.0,
    "human": 37.0,
}

# NLP — CDCgov/Opioid_Involvement_NLP vendor path
NLP_INSIGHTS_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_nlp_insights.json"

# Demographics data (CDC published summary tables)
DEMOGRAPHICS_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_demographics.json"
CDC_NLP_VENDOR_DIR = "opioid_track/vendor/Opioid_Involvement_NLP"
SPL_OPIOID_SECTIONS = {
    "boxed_warning":       "34066-1",
    "indications":         "34067-9",
    "dosage_admin":        "34068-7",
    "warnings_precautions":"43685-7",
    "adverse_reactions":   "34084-4",
    "drug_interactions":   "34073-7",
    "abuse_dependence":    "42227-9",
    "overdosage":          "34088-5",
    "clinical_pharmacology":"34090-1",
}

# Dashboard — reference repos
DASH_DEMO_VENDOR_DIR = "opioid_track/vendor/dash-opioid-epidemic-demo"
DASHBOARD_TITLE = "TruPharma Opioid Intelligence"
DASHBOARD_PORT = 8502

# Knowledge chunks for RAG
KNOWLEDGE_CHUNKS_DIR = f"{OPIOID_DATA_DIR}/knowledge_chunks"
CHUNK_SIZE_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 100

