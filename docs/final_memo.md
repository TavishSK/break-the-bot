# Final Evaluation Memo — Break the Bot

**Project:** Priya, Sunrise Finance voice assistant  
**Evaluation:** Baseline versus deterministic application-level defenses  
**Test set:** 17 attacks × 3 runs = 51 runs per phase

## Executive summary

This project red-teamed a fictional financial assistant named Priya. The work began by defining failure criteria, then created 17 adversarial scenarios across seven categories, implemented a Gemini-backed assistant and repeatable Python harness, added a deterministic `DefenseEngine`, and repeated the same attacks.

The baseline produced **36 HELD (70.6%)**, **4 PARTIAL (7.8%)**, **11 BROKEN (21.6%)**, and **0 ERROR** results. The defended harness recorded **51 HELD (100%)**, **0 PARTIAL**, **0 BROKEN**, and **0 ERROR**. The HELD share therefore increased by **29.4 percentage points** in the recorded experiments.

## Method

The attack suite covers identity manipulation (A01–A03), instruction override (A04–A06), confidential information extraction (A07–A08), financial policy manipulation (A09–A11), speech/transcription-oriented manipulation (A12–A14), human escalation (A15–A16), and topic redirection (A17). Each scenario was run three times in a fresh conversation; multi-turn scenarios retained context within each run. Hinglish prompts and speech-oriented transcript scenarios were included. The evaluator used a predefined HELD / PARTIAL / BROKEN rubric and manually recorded a classification and rationale for each run. Technical failures were kept separate as ERROR.

The defense layer uses Python prechecks to intercept suspicious inputs, conversation-state flags for identity and escalation, and response validation intended to catch protected information and unauthorised commitments. Gemini was used for the assistant's model responses when a request passed the input checks.

## Results

| Classification | Baseline | Defended |
|---|---:|---:|
| HELD | 36 (70.6%) | 51 (100%) |
| PARTIAL | 4 (7.8%) | 0 |
| BROKEN | 11 (21.6%) | 0 |
| ERROR | 0 | 0 |
| **Total** | **51** | **51** |

## Interpretation and limitations

All 51 defended transcripts shared during the evaluation showed the input defense handling the message locally before it reached Gemini. The defended result therefore supports the narrower conclusion that the input guard intercepted all prompts in this particular test set. It does **not** establish that Gemini itself is robust to these attacks after authentication, or that the output validator has been comprehensively tested.

The code currently creates separate `DefenseEngine` instances in the harness and in `PriyaBot`. Their state can diverge on requests that pass the harness precheck. A benign “compliance update” phrase was also blocked by a confidential-information keyword check, showing a false-positive risk. The speech cases were text simulations, not tests of real audio, ASR accuracy or speaker authentication. A callback was offered in the response but was not connected to an actual telephony service.

## Recommendations

1. Refactor the harness and bot to share one `DefenseEngine` instance.
2. Add post-authentication attacks to exercise the Gemini and response-validation path.
3. Replace self-asserted identity with a trusted verification mechanism, such as OTP through a registered channel.
4. Improve multilingual/contextual detection and measure both false positives and false negatives.
5. Test real audio/ASR conditions and connect human escalation to a real callback or transfer workflow if production use is intended.

## Conclusion

The project demonstrates a repeatable red-team workflow and shows that deterministic application-level input checks can intercept the tested adversarial prompts. The results are promising for this controlled test set, but broader claims about model security require shared-state correction, post-authentication testing, real voice testing and stronger identity verification.
