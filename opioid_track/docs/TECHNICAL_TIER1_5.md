# Opioid Track -- Technical Architecture (Tier 1.5)
**Version:** 1.5.0
**Parent Project:** TruPharma Clinical Intelligence

---

## 1. Overview
Upgrading Tier 1 to Tier 1.5 adds clinical depth and real-time syncing.

**Key changes:**
- Expansion from Ingredient RxCUIs (IN/MIN) to Product RxCUIs (SCD/SBD).
- Syncing NDCs > 2018 using OpenFDA API.

## 2. Updated API Endpoints
**OpenFDA NDC API:**
```
GET https://api.fda.gov/drug/ndc.json?search=pharm_class:"opioid"+AND+marketing_start_date:[20190101+TO+20251231]&limit=100
```
