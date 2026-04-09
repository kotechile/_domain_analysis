# Domain Scoring V2 Spec

## Goal

Score auction domains more like an investor would evaluate them:

- favor liquidity and resale potential over raw age
- reward clean brandable and commercial strings
- treat TLD quality contextually
- reject weak inventory early

## Problems With V1

- Age was overweighted at 40%.
- NLP-style semantic scoring was too generic for domain investing.
- Compound word segmentation was weak.
- The model had almost no penalties for low-liquidity patterns.
- Different code paths could apply different heuristics.

## V2 Principles

1. Hard filters remove inventory we do not want to rank at all.
2. The total score should reflect resale quality, not just lexical cleanliness.
3. Age is a bonus, not the main driver.
4. `.com` remains the default strongest TLD, while `.ai`, `.io`, and `.org` are contextual.
5. Short random strings should not beat clean commercial compounds by default.

## Stage 1: Hard Filters

- TLD must be in the configured allowlist.
- Root label length must be within the configured maximum.
- No hyphens or special characters.
- Numeric-heavy names fail unless the number is commercially meaningful.
- Extremely unpronounceable consonant clusters fail.
- Filler-heavy compounds such as `get`, `my`, `best`, `online`, `top` fail.
- Domains must be segmentable into tradable tokens or be plausible liquid/pronounceable brandables.

## Stage 2: Tokenization

Use weighted domain segmentation instead of plain regex splitting.

Inputs:
- word frequency dictionary
- industry keyword dictionary
- curated business-native terms

Behavior:
- exact dictionary words are rewarded
- clean two-word compounds are rewarded
- low-value filler tokens are penalized
- if a string cannot be segmented, it must still pass pronounceability or liquid-short heuristics

## Stage 3: Sub-Scores

All sub-scores are normalized to 0-100.

### 1. Liquidity Score: 35%

Measures how broadly resellable the name is.

Signals:
- strong `.com`
- clean one-word names
- clean two-word compounds
- short liquid-style names
- pronounceability
- no filler terms
- no weak numeric patterns

### 2. Brandability Score: 25%

Measures memorability and radio-test strength.

Signals:
- 4-10 character sweet spot
- pronounceability
- clean sound pattern
- no awkward repeats
- no low-signal digits

### 3. Commercial Intent Score: 20%

Measures likely end-user demand.

Signals:
- exact business/category words
- strong industry keywords
- one-word category terms
- clean two-word business compounds
- broad buyer appeal

### 4. TLD Score: 10%

Context-sensitive TLD quality:

- `.com`: strongest default
- `.ai`: strong when the root is AI-native
- `.io`: strong for tech/dev/tool patterns
- `.org`: stronger for mission/community/public-interest terms
- `.co` and `.net`: moderate fallback value

### 5. Age Score: 10%

Smooth age bonus:

- `<1y`: 5
- `1-3y`: 20
- `3-5y`: 45
- `5-10y`: 65
- `10-15y`: 85
- `15y+`: 100

Age helps, but cannot dominate the score.

## Total Score Formula

```text
total_score =
  (liquidity_score * 0.35) +
  (brandability_score * 0.25) +
  (commercial_intent_score * 0.20) +
  (tld_score * 0.10) +
  (age_score * 0.10)
```

## Backward Compatibility

To avoid breaking existing consumers:

- `lexical_frequency_score` now carries the V2 liquidity proxy
- `semantic_value_score` now carries the average of brandability and commercial intent
- `total_meaning_score` remains the final 0-100 score

Additional optional fields exposed by the scoring model:

- `tld_score`
- `liquidity_score`
- `brandability_score`
- `commercial_intent_score`

## First-Pass Implementation Scope

Included now:

- investor-oriented hard filters
- weighted compound segmentation
- contextual TLD handling
- new V2 score formula
- centralized scoring logic used by both direct and auction flows

Deferred for later:

- trademark risk screening
- comparable sales integration
- CPC / advertiser density signals
- end-user count estimation
- historical sell-through calibration
