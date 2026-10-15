# CARNA-AI Pilot Dataset (v0.1, structured data layer)

Built from: CARNA-AI Team Training Document, your Top-100 raga sheet, and the Carnatic Varnam Dataset v1.1 (CompMusic/UPF, audio CC BY 3.0 - cite Koduri et al. 2014).
Generated 2026-10-08. **Nothing here is expert-verified yet.** Every musical rule must pass your Music Domain Expert (Team Rule 4).

## What is and is not included
| Included | Not included (needs you) |
|---|---|
| 16 pilot ragas with scales, pitch classes, class, vakra flag | Audio (use the varnam ZIP via `audio_manifest.csv`) |
| Swara reference (semitone, cents, 5-limit ratios) | Prayogas / characteristic phrases (`prayoga_template.csv`, empty) |
| Scale-derived swara transitions (NOT prayogas) | Gamaka definitions (`gamaka_template.csv`, empty) |
| 120 raga-pair comparisons for the composer module | Film-song labels (`film_song_template.csv`, empty) |
| Manifest of 28 labelled varnam recordings + tonics + splits | Concert / alapana / film audio |
| Glossary from the training document | |
| SQLite DB (`carna_ai_pilot.db`) with all tables | |

## Files
- `ragas_knowledge_base.csv/.json` - one row per pilot raga. `pitch_classes` = semitones above Sa (0-11) used in arohanam or avarohanam. `audio_match`: exact / possible_alias / none. Scales come from your sheet; `source_confidence_in_your_sheet` and `source_notes` carry its "Check" flags (e.g. Ahiri's parent is disputed).
- `swara_reference.csv` - 16 swarasthanas. Enharmonic pairs share a pitch (R2=G1, R3=G2, D2=N1, D3=N2). Just ratios are a common 5-limit reference only; real intonation varies by singer and raga, so use as a starting point, not ground truth.
- `scale_transitions.csv` - consecutive swara pairs from arohanam/avarohanam. These show scale grammar only; they are not characteristic phrases.
- `raga_pair_matrix.csv` - shared / unique pitch classes and Jaccard similarity for every pilot pair. Hamsadhwani+Ahiri (the document's composer example) share only semitones 0, 4, 7 (Jaccard 0.33). Pitch-class overlap ignores gamaka and phrasing, so it is a first filter only.
- `audio_manifest.csv` - the 28 varnam recordings with paths inside the ZIP, singer, tonic, technical specs, taala `.svl` and notation `.yaml` paths. `suggested_split`: test = singers vignesh + dharini (covers all 7 ragas, train still has every raga); keep singer-level splits to avoid leakage. `qc_flag=tonic_unverified` for badrinarayanan (see earlier report).
- `glossary.csv`, `*_template.csv`, `carna_ai_pilot.db`.

## Known limitations
1. Only 7 of 16 pilot ragas have audio (Mohanam, Mechakalyani*, Sahana, Abhogi, Begada, Saveri, Sriragam*; *alias match). Mayamalavagowla, Dheerasankarabharanam, Kharaharapriya, Hanumatodi, Harikambhoji, Bhairavi, Kambhoji, Hamsadhwani and Ahiri have none.
2. 3-5 recordings per raga, one varnam per raga: use for pipeline testing, not for a trustworthy classifier.
3. Vakra and bhashanga detail in the scales is simplified; the sheet's own notes say so.
4. Varnam yaml notation uses different subscripts than your sheet (e.g. G1 vs G2); do not join on swara names, join on semitones.
