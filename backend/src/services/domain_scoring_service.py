"""
Domain scoring service tuned for auction-style domain investing.
"""

import json
import math
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import structlog

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    structlog.get_logger().warning("spaCy not available, using fallback tokenization")

from models.domain_analysis import NamecheapDomain, ScoredDomain
from utils.config import get_settings
from utils.date_utils import parse_iso_datetime

logger = structlog.get_logger()

AI_NATIVE_TERMS = {
    "agent",
    "agents",
    "ai",
    "bot",
    "bots",
    "copilot",
    "gpt",
    "inference",
    "llm",
    "model",
    "models",
    "neural",
    "prompt",
    "prompts",
}

TECH_NATIVE_TERMS = {
    "api",
    "app",
    "apps",
    "build",
    "cloud",
    "code",
    "data",
    "dev",
    "digital",
    "flow",
    "forge",
    "hub",
    "kit",
    "lab",
    "labs",
    "logic",
    "ops",
    "pay",
    "stack",
    "sync",
    "tech",
}

ORG_NATIVE_TERMS = {
    "care",
    "cause",
    "charity",
    "church",
    "community",
    "education",
    "foundation",
    "help",
    "impact",
    "justice",
    "mission",
    "nonprofit",
    "open",
    "public",
    "relief",
    "school",
}

FILLER_TERMS = {
    "best",
    "buy",
    "deals",
    "get",
    "go",
    "hq",
    "my",
    "now",
    "online",
    "pro",
    "site",
    "store",
    "the",
    "top",
    "web",
}

MEANINGFUL_NUMBERS = {"24", "360", "365", "101", "247", "911"}


class DomainScoringService:
    """Service for investor-oriented domain filtering and scoring."""

    def __init__(self):
        self.settings = get_settings()
        self.tier_1_tlds = set(self.settings.TIER_1_TLDS)
        self.max_length = self.settings.MAX_DOMAIN_LENGTH
        self.max_numbers = self.settings.MAX_NUMBERS
        self.min_word_ratio = self.settings.MIN_WORD_RECOGNITION_RATIO

        self.word_frequency = self._load_word_frequency()
        self.industry_keywords = self._load_industry_keywords()
        self.dictionary_words = set(self.word_frequency.keys()) | self.industry_keywords

        self.nlp = None
        self._init_spacy()

    def _load_word_frequency(self) -> Dict[str, int]:
        """Load word frequency data from JSON file."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(
                base_dir, "src", "services", "scoring_data", "word_frequency.json"
            )
            with open(data_path, "r") as f:
                data = json.load(f)
                logger.info("Loaded word frequency data", word_count=len(data))
                return data
        except Exception as e:
            logger.error("Failed to load word frequency data", error=str(e))
            return {}

    def _load_industry_keywords(self) -> Set[str]:
        """Load industry keywords from JSON file and flatten to a set."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(
                base_dir, "src", "services", "scoring_data", "industry_keywords.json"
            )
            with open(data_path, "r") as f:
                data = json.load(f)
                keywords: Set[str] = set()
                for _, words in data.items():
                    keywords.update(word.lower() for word in words)
                logger.info("Loaded industry keywords", keyword_count=len(keywords))
                return keywords
        except Exception as e:
            logger.error("Failed to load industry keywords", error=str(e))
            return set()

    def _init_spacy(self):
        """Initialize spaCy lazily when available."""
        if not SPACY_AVAILABLE:
            return

        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model")
        except OSError:
            logger.warning(
                "spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm"
            )
            self.nlp = None
        except Exception as e:
            logger.error("Failed to load spaCy model", error=str(e))
            self.nlp = None

    def _extract_domain_parts(self, domain_name: str) -> Tuple[str, str]:
        """Extract root label and TLD from a full domain."""
        if "." not in domain_name:
            return domain_name.lower(), ""

        parts = domain_name.rsplit(".", 1)
        if len(parts) == 2:
            return parts[0].lower(), "." + parts[1].lower()
        return domain_name.lower(), ""

    def _candidate_token_weight(self, token: str) -> float:
        """Return a segmentation weight for a candidate token."""
        if token in FILLER_TERMS:
            return 1.0
        if token in self.industry_keywords:
            return 7.0
        if token in self.word_frequency:
            rank = self.word_frequency[token]
            return max(2.0, 8.0 - math.log10(max(rank, 1)))
        return 0.0

    def _segment_compound(self, name: str) -> List[str]:
        """
        Segment a lowercase label into likely words using a weighted DP.

        This is more domain-aware than the old regex split and better suited to
        compounds like 'healthpilot' or 'fundstack'.
        """
        if not name:
            return []

        if name in self.dictionary_words:
            return [name]

        n = len(name)
        best: Dict[int, Tuple[float, List[str]]] = {0: (0.0, [])}

        for i in range(n):
            if i not in best:
                continue

            current_score, current_tokens = best[i]
            for j in range(i + 2, min(n, i + 13) + 1):
                token = name[i:j]
                weight = self._candidate_token_weight(token)
                if weight <= 0:
                    continue

                candidate_score = current_score + weight
                existing = best.get(j)
                candidate_tokens = current_tokens + [token]
                if existing is None or candidate_score > existing[0]:
                    best[j] = (candidate_score, candidate_tokens)

        if n in best:
            tokens = best[n][1]
            covered = sum(len(token) for token in tokens)
            if covered >= max(4, int(0.75 * len(name))):
                return tokens

        return []

    def _is_pronounceable(self, label: str) -> bool:
        """Simple radio-test proxy for brandables."""
        if not label or not label.isalnum():
            return False

        letters_only = re.sub(r"\d", "", label)
        if not letters_only:
            return False

        vowel_ratio = sum(1 for ch in letters_only if ch in "aeiouy") / len(letters_only)
        if vowel_ratio < 0.2 or vowel_ratio > 0.75:
            return False

        if re.search(r"[^aeiouy]{5,}", letters_only):
            return False

        if re.search(r"(.)\1\1", letters_only):
            return False

        return True

    def _looks_like_liquid_short(self, label: str) -> bool:
        """Heuristic for short liquid-style names and acronyms."""
        if not label.isalpha():
            return False

        if len(label) <= 3:
            return True

        if len(label) == 4:
            return self._is_pronounceable(label) or label in self.dictionary_words

        return False

    def _has_meaningful_number(self, label: str) -> bool:
        """Allow a few commercial numeric patterns without treating all digits equally."""
        for number in MEANINGFUL_NUMBERS:
            if label.endswith(number) or label.startswith(number):
                return True
        return False

    def _tokenize_domain(self, domain_name: str, fast_mode: bool = False) -> List[str]:
        """Tokenize a domain into investor-meaningful components."""
        if not domain_name:
            return []

        segmented = self._segment_compound(domain_name)
        if segmented:
            return segmented

        camel_tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", domain_name)
        if camel_tokens:
            return [token.lower() for token in camel_tokens]

        if self._looks_like_liquid_short(domain_name) or self._is_pronounceable(domain_name):
            return [domain_name.lower()]

        if not fast_mode and self.nlp:
            try:
                doc = self.nlp(domain_name)
                tokens = [token.text.lower() for token in doc if token.is_alpha]
                if tokens:
                    return tokens
            except Exception as e:
                logger.warning("spaCy tokenization failed", domain=domain_name, error=str(e))

        return []

    def _calculate_age_score(self, domain: NamecheapDomain) -> float:
        """Return a smoother 0-100 age score with a lower final weight."""
        if not domain.registered_date:
            return 0.0

        try:
            reg_date = (
                parse_iso_datetime(domain.registered_date)
                if isinstance(domain.registered_date, str)
                else domain.registered_date
            )
            if not reg_date:
                return 0.0

            years_old = (datetime.now(reg_date.tzinfo) - reg_date).days / 365.25

            if years_old >= 15:
                return 100.0
            if years_old >= 10:
                return 85.0
            if years_old >= 5:
                return 65.0
            if years_old >= 3:
                return 45.0
            if years_old >= 1:
                return 20.0
            return 5.0
        except Exception as e:
            logger.warning("Failed to calculate age score", domain=domain.name, error=str(e))
            return 0.0

    def _has_term_family(self, label: str, tokens: List[str], candidates: Set[str]) -> bool:
        """Check token or substring membership for contextual TLD scoring."""
        token_set = set(tokens)
        if token_set & candidates:
            return True
        return any(term in label for term in candidates if len(term) >= 3)

    def _calculate_tld_score(self, label: str, tld: str, tokens: List[str]) -> float:
        """Context-sensitive TLD score."""
        if tld == ".com":
            return 100.0
        if tld == ".ai":
            return 85.0 if self._has_term_family(label, tokens, AI_NATIVE_TERMS) else 55.0
        if tld == ".io":
            if self._has_term_family(label, tokens, AI_NATIVE_TERMS | TECH_NATIVE_TERMS):
                return 78.0
            return 58.0
        if tld == ".org":
            return 72.0 if self._has_term_family(label, tokens, ORG_NATIVE_TERMS) else 52.0
        if tld == ".co":
            return 60.0
        if tld == ".net":
            return 56.0

        return 35.0

    def _calculate_liquidity_score(self, label: str, tld: str, tokens: List[str]) -> float:
        """Approximate investor liquidity and resale breadth."""
        score = 30.0
        length = len(label)
        token_count = len(tokens)
        recognized_tokens = sum(1 for token in tokens if token in self.dictionary_words)

        if tld == ".com":
            score += 15.0
        elif tld in {".ai", ".io"}:
            score += 8.0

        if self._looks_like_liquid_short(label):
            score += 28.0
        elif token_count == 1 and recognized_tokens == 1 and 4 <= length <= 10:
            score += 32.0
        elif token_count == 2 and recognized_tokens >= 1 and length <= 12:
            score += 24.0
        elif self._is_pronounceable(label) and 5 <= length <= 10:
            score += 20.0
        else:
            score += max(0.0, 18.0 - abs(length - 8) * 3.0)

        if re.search(r"\d", label):
            score -= 18.0 if not self._has_meaningful_number(label) else 6.0

        if any(token in FILLER_TERMS for token in tokens):
            score -= 12.0

        if re.search(r"[^aeiouy]{5,}", label):
            score -= 10.0

        return max(0.0, min(100.0, score))

    def _calculate_brandability_score(self, label: str, tokens: List[str]) -> float:
        """Score memorability, radio test, and cleanliness."""
        score = 25.0
        length = len(label)

        if 4 <= length <= 10:
            score += 25.0
        elif 11 <= length <= 12:
            score += 15.0
        elif 13 <= length <= 15:
            score += 5.0

        if self._is_pronounceable(label):
            score += 25.0

        if len(tokens) == 2 and sum(len(token) for token in tokens) == length:
            score += 12.0
        elif len(tokens) == 1 and tokens[0] == label and label in self.dictionary_words:
            score += 18.0
        elif self._looks_like_liquid_short(label):
            score += 12.0

        if re.search(r"\d", label):
            score -= 20.0 if not self._has_meaningful_number(label) else 8.0

        if re.search(r"(.)\1\1", label):
            score -= 12.0

        if any(token in FILLER_TERMS for token in tokens):
            score -= 10.0

        return max(0.0, min(100.0, score))

    def _calculate_commercial_intent_score(self, label: str, tokens: List[str]) -> float:
        """Score probable end-user demand and business usability."""
        if not tokens:
            return 20.0 if self._is_pronounceable(label) else 5.0

        score = 15.0
        token_set = set(tokens)
        industry_hits = sum(1 for token in tokens if token in self.industry_keywords)
        dictionary_hits = sum(1 for token in tokens if token in self.word_frequency)

        score += min(30.0, dictionary_hits * 15.0)
        score += min(25.0, industry_hits * 18.0)

        if len(tokens) == 1 and tokens[0] in self.word_frequency and 4 <= len(tokens[0]) <= 10:
            score += 25.0
        elif len(tokens) == 2:
            score += 20.0
        elif len(tokens) > 2:
            score -= 8.0

        if token_set & (AI_NATIVE_TERMS | TECH_NATIVE_TERMS | ORG_NATIVE_TERMS):
            score += 10.0

        if any(token in FILLER_TERMS for token in tokens):
            score -= 18.0

        if re.search(r"\d", label):
            score -= 12.0 if not self._has_meaningful_number(label) else 4.0

        return max(0.0, min(100.0, score))

    def _calculate_lexical_frequency_score(self, domain: NamecheapDomain) -> float:
        """
        Backward-compatible field name.

        In v2 this acts as the liquidity proxy because that is much closer to
        what investors care about than raw lexical frequency.
        """
        label, tld = self._extract_domain_parts(domain.name.lower())
        tokens = self._tokenize_domain(label)
        return self._calculate_liquidity_score(label, tld, tokens)

    def _calculate_semantic_value(self, domain: NamecheapDomain, fast_mode: bool = False) -> float:
        """
        Backward-compatible field name.

        In v2 this becomes the average of brandability and commercial intent.
        """
        label, _ = self._extract_domain_parts(domain.name.lower())
        tokens = self._tokenize_domain(label, fast_mode=fast_mode)
        brandability = self._calculate_brandability_score(label, tokens)
        commercial = self._calculate_commercial_intent_score(label, tokens)
        return round((brandability + commercial) / 2.0, 2)

    def _stage1_filter(
        self, domain: NamecheapDomain, fast_mode: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Hard filters for obviously weak or unsupported inventory."""
        domain_name = domain.name.lower()
        label, tld = self._extract_domain_parts(domain_name)

        if tld not in self.tier_1_tlds:
            return False, f"TLD {tld} not in whitelist"

        if len(label) > self.max_length:
            return False, f"Domain name exceeds {self.max_length} characters"

        if "-" in label or re.search(r"[^a-zA-Z0-9]", label):
            return False, "Contains hyphens or special characters"

        number_count = len(re.findall(r"\d", label))
        if number_count > self.max_numbers:
            return False, f"Contains more than {self.max_numbers} numbers"

        if number_count > 0 and not self._has_meaningful_number(label) and not self._looks_like_liquid_short(label):
            return False, "Contains low-signal numbers"

        if re.search(r"[^aeiouy]{6,}", label):
            return False, "Fails basic pronounceability check"

        tokens = self._tokenize_domain(label, fast_mode=fast_mode)
        if not tokens:
            return False, "Could not segment domain into tradable tokens"

        recognized_count = sum(1 for token in tokens if token.lower() in self.dictionary_words)
        recognition_ratio = recognized_count / len(tokens) if tokens else 0
        required_ratio = self.min_word_ratio or 0.0
        if recognition_ratio < required_ratio:
            return False, f"Less than {required_ratio * 100}% recognized words"

        if any(token in FILLER_TERMS for token in tokens) and len(tokens) >= 2:
            return False, "Contains low-value filler terms"

        return True, None

    def score_domain(self, domain: NamecheapDomain, fast_mode: bool = False) -> ScoredDomain:
        """Score a single domain using the v2 investor-oriented model."""
        passed, reason = self._stage1_filter(domain, fast_mode=fast_mode)
        if not passed:
            return ScoredDomain(
                domain=domain,
                filter_status="FAIL",
                filter_reason=reason,
                total_meaning_score=None,
                age_score=None,
                lexical_frequency_score=None,
                semantic_value_score=None,
                tld_score=None,
                liquidity_score=None,
                brandability_score=None,
                commercial_intent_score=None,
                rank=None,
            )

        label, tld = self._extract_domain_parts(domain.name.lower())
        tokens = self._tokenize_domain(label, fast_mode=fast_mode)

        age_score = self._calculate_age_score(domain)
        tld_score = self._calculate_tld_score(label, tld, tokens)
        liquidity_score = self._calculate_liquidity_score(label, tld, tokens)
        brandability_score = self._calculate_brandability_score(label, tokens)
        commercial_intent_score = self._calculate_commercial_intent_score(label, tokens)
        semantic_value_score = round((brandability_score + commercial_intent_score) / 2.0, 2)

        total_score = (
            (liquidity_score * 0.35)
            + (brandability_score * 0.25)
            + (commercial_intent_score * 0.20)
            + (tld_score * 0.10)
            + (age_score * 0.10)
        )

        return ScoredDomain(
            domain=domain,
            filter_status="PASS",
            filter_reason=None,
            total_meaning_score=round(total_score, 2),
            age_score=round(age_score, 2),
            lexical_frequency_score=round(liquidity_score, 2),
            semantic_value_score=semantic_value_score,
            tld_score=round(tld_score, 2),
            liquidity_score=round(liquidity_score, 2),
            brandability_score=round(brandability_score, 2),
            commercial_intent_score=round(commercial_intent_score, 2),
            rank=None,
        )

    def score_domains(self, domains: List[NamecheapDomain]) -> List[ScoredDomain]:
        """Score multiple domains and rank the passed set."""
        logger.info("Starting domain scoring", domain_count=len(domains))

        scored_domains: List[ScoredDomain] = []
        for i, domain in enumerate(domains):
            try:
                scored = self.score_domain(domain)
                scored_domains.append(scored)

                if (i + 1) % 1000 == 0:
                    logger.info("Scoring progress", processed=i + 1, total=len(domains))
            except Exception as e:
                logger.error("Failed to score domain", domain=domain.name, error=str(e))
                scored_domains.append(
                    ScoredDomain(
                        domain=domain,
                        filter_status="FAIL",
                        filter_reason=f"Scoring error: {str(e)}",
                        total_meaning_score=None,
                        age_score=None,
                        lexical_frequency_score=None,
                        semantic_value_score=None,
                        tld_score=None,
                        liquidity_score=None,
                        brandability_score=None,
                        commercial_intent_score=None,
                        rank=None,
                    )
                )

        scored_domains.sort(
            key=lambda item: (item.filter_status != "PASS", -(item.total_meaning_score or 0.0))
        )

        rank = 1
        for scored in scored_domains:
            if scored.filter_status == "PASS":
                scored.rank = rank
                rank += 1

        passed_count = sum(1 for item in scored_domains if item.filter_status == "PASS")
        logger.info(
            "Domain scoring complete",
            total=len(domains),
            passed=passed_count,
            failed=len(domains) - passed_count,
        )

        return scored_domains
