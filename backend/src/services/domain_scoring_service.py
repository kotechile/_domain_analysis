"""
Domain Scoring Service for filtering and ranking domains
"""

import re
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import structlog

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    structlog.get_logger().warning("spaCy not available, using fallback tokenization")

from models.domain_analysis import NamecheapDomain, ScoredDomain
from utils.config import get_settings

logger = structlog.get_logger()


class DomainScoringService:
    """Service for scoring and filtering domains"""
    
    def __init__(self):
        self.settings = get_settings()
        self.tier_1_tlds = set(self.settings.TIER_1_TLDS)
        self.max_length = self.settings.MAX_DOMAIN_LENGTH
        self.max_numbers = self.settings.MAX_NUMBERS
        self.min_word_ratio = self.settings.MIN_WORD_RECOGNITION_RATIO
        
        # Load word frequency data
        self.word_frequency = self._load_word_frequency()
        
        # Load industry keywords
        self.industry_keywords = self._load_industry_keywords()
        
        # Initialize spaCy model (lazy loading)
        self.nlp = None
        self._init_spacy()
    
    def _load_word_frequency(self) -> Dict[str, int]:
        """Load word frequency data from JSON file"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(base_dir, 'src', 'services', 'scoring_data', 'word_frequency.json')
            with open(data_path, 'r') as f:
                data = json.load(f)
                logger.info("Loaded word frequency data", word_count=len(data))
                return data
        except Exception as e:
            logger.error("Failed to load word frequency data", error=str(e))
            return {}
    
    def _load_industry_keywords(self) -> set:
        """Load industry keywords from JSON file and flatten to set"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(base_dir, 'src', 'services', 'scoring_data', 'industry_keywords.json')
            with open(data_path, 'r') as f:
                data = json.load(f)
                # Flatten all categories into a single set
                keywords = set()
                for category, words in data.items():
                    keywords.update(words)
                logger.info("Loaded industry keywords", keyword_count=len(keywords))
                return keywords
        except Exception as e:
            logger.error("Failed to load industry keywords", error=str(e))
            return set()
    
    def _init_spacy(self):
        """Initialize spaCy model (lazy loading)"""
        if not SPACY_AVAILABLE:
            return
        
        try:
            # Try to load the model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        except Exception as e:
            logger.error("Failed to load spaCy model", error=str(e))
            self.nlp = None
    
    def _extract_domain_parts(self, domain_name: str) -> Tuple[str, str]:
        """Extract domain name and TLD from full domain"""
        if '.' not in domain_name:
            return domain_name, ''
        
        parts = domain_name.rsplit('.', 1)
        if len(parts) == 2:
            return parts[0].lower(), '.' + parts[1].lower()
        return domain_name.lower(), ''
    
    def _stage1_filter(self, domain: NamecheapDomain) -> Tuple[bool, Optional[str]]:
        """
        Stage 1: Absolute filtering (hard stops)
        Returns: (passed, reason_if_failed)
        """
        domain_name = domain.name.lower()
        name_part, tld = self._extract_domain_parts(domain_name)
        
        # Filter 3.1: TLD Tier
        if tld not in self.tier_1_tlds:
            return False, f"TLD {tld} not in whitelist"
        
        # Filter 3.2: Length
        if len(name_part) > self.max_length:
            return False, f"Domain name exceeds {self.max_length} characters"
        
        # Filter 3.3: Punctuation
        if '-' in name_part or re.search(r'[^a-zA-Z0-9]', name_part):
            return False, "Contains hyphens or special characters"
        
        # Filter 3.4: Numerics
        number_count = len(re.findall(r'\d', name_part))
        if number_count > self.max_numbers:
            return False, f"Contains more than {self.max_numbers} numbers"
        
        # Filter 3.5: Pronunciation (tokenization)
        tokens = self._tokenize_domain(name_part)
        if not tokens:
            return False, "Could not tokenize domain"
        
        recognized_count = sum(1 for token in tokens if token.lower() in self.word_frequency)
        recognition_ratio = recognized_count / len(tokens) if tokens else 0
        
        if recognition_ratio < self.min_word_ratio:
            return False, f"Less than {self.min_word_ratio*100}% recognized words"
        
        return True, None
    
    def _tokenize_domain(self, domain_name: str) -> List[str]:
        """Tokenize domain name into words"""
        # Try spaCy first
        if self.nlp:
            try:
                doc = self.nlp(domain_name)
                # Extract tokens that are alphabetic
                tokens = [token.text for token in doc if token.is_alpha]
                if tokens:
                    return tokens
            except Exception as e:
                logger.warning("spaCy tokenization failed", domain=domain_name, error=str(e))
        
        # Fallback: heuristic splitting (camelCase, etc.)
        # Split on capital letters
        tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', domain_name)
        if tokens:
            return tokens
        
        # Last resort: return as single token
        return [domain_name] if domain_name else []
    
    def _calculate_age_score(self, domain: NamecheapDomain) -> float:
        """Calculate age score based on registered_date"""
        if not domain.registered_date:
            return 0.0
        
        try:
            if isinstance(domain.registered_date, str):
                reg_date = datetime.fromisoformat(domain.registered_date.replace('Z', '+00:00'))
            else:
                reg_date = domain.registered_date
            
            years_old = (datetime.now(reg_date.tzinfo) - reg_date).days / 365.25
            
            if years_old >= 10:
                return 100.0
            elif years_old >= 5:
                return 50.0
            else:
                return 20.0
        except Exception as e:
            logger.warning("Failed to calculate age score", domain=domain.name, error=str(e))
            return 0.0
    
    def _calculate_lexical_frequency_score(self, domain: NamecheapDomain) -> float:
        """Calculate Lexical Frequency Score (LFS)"""
        domain_name = domain.name.lower()
        name_part, _ = self._extract_domain_parts(domain_name)
        tokens = self._tokenize_domain(name_part)
        
        if not tokens:
            return 0.0
        
        scores = []
        for token in tokens:
            token_lower = token.lower()
            rank = self.word_frequency.get(token_lower, 10000)  # Default to worst rank
            
            # Convert rank to score: Rank 1 = 100, Rank 10000 = 1
            # Linear interpolation
            if rank <= 1:
                score = 100.0
            elif rank >= 10000:
                score = 1.0
            else:
                # Linear interpolation: score = 100 - (rank-1) * (99/9999)
                score = 100.0 - (rank - 1) * (99.0 / 9999.0)
            
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_semantic_value(self, domain: NamecheapDomain) -> float:
        """Calculate Semantic Value (POS + Industry Relevance)"""
        domain_name = domain.name.lower()
        name_part, _ = self._extract_domain_parts(domain_name)
        tokens = self._tokenize_domain(name_part)
        
        if not tokens:
            return 0.0
        
        pos_score = 0.0
        irs_score = 0.0
        
        # POS tagging
        if self.nlp:
            try:
                doc = self.nlp(' '.join(tokens))
                for token in doc:
                    pos = token.pos_
                    if pos == 'NOUN' or pos == 'PROPN':  # Noun or Proper Noun
                        pos_score += 30.0
                    elif pos == 'VERB':
                        pos_score += 20.0
                    elif pos == 'ADJ':  # Adjective
                        pos_score += 15.0
            except Exception as e:
                logger.warning("POS tagging failed", domain=domain.name, error=str(e))
        
        # Industry Relevance Score
        for token in tokens:
            if token.lower() in self.industry_keywords:
                irs_score += 20.0
        
        # Average and normalize
        token_count = len(tokens)
        if token_count > 0:
            pos_score = pos_score / token_count
            irs_score = irs_score / token_count
        
        # Combine: average of POS and IRS, then normalize to 0-100
        sv = (pos_score + irs_score) / 2.0
        return min(100.0, max(0.0, sv))
    
    def score_domain(self, domain: NamecheapDomain) -> ScoredDomain:
        """Score a single domain"""
        # Stage 1: Filtering
        passed, reason = self._stage1_filter(domain)
        
        if not passed:
            return ScoredDomain(
                domain=domain,
                filter_status='FAIL',
                filter_reason=reason,
                total_meaning_score=None,
                age_score=None,
                lexical_frequency_score=None,
                semantic_value_score=None,
                rank=None
            )
        
        # Stage 2: Scoring
        age_score = self._calculate_age_score(domain)
        lfs_score = self._calculate_lexical_frequency_score(domain)
        sv_score = self._calculate_semantic_value(domain)
        
        # Total Meaning Score
        total_score = (age_score * 0.40) + (lfs_score * 0.30) + (sv_score * 0.30)
        
        return ScoredDomain(
            domain=domain,
            filter_status='PASS',
            filter_reason=None,
            total_meaning_score=round(total_score, 2),
            age_score=round(age_score, 2),
            lexical_frequency_score=round(lfs_score, 2),
            semantic_value_score=round(sv_score, 2),
            rank=None  # Will be set after sorting
        )
    
    def score_domains(self, domains: List[NamecheapDomain]) -> List[ScoredDomain]:
        """
        Score a list of domains
        
        Args:
            domains: List of NamecheapDomain objects
            
        Returns:
            List of ScoredDomain objects, sorted by total_meaning_score DESC
        """
        logger.info("Starting domain scoring", domain_count=len(domains))
        
        scored_domains = []
        for i, domain in enumerate(domains):
            try:
                scored = self.score_domain(domain)
                scored_domains.append(scored)
                
                # Log progress every 1000 domains
                if (i + 1) % 1000 == 0:
                    logger.info("Scoring progress", processed=i + 1, total=len(domains))
            except Exception as e:
                logger.error("Failed to score domain", domain=domain.name, error=str(e))
                # Create FAIL entry for error case
                scored_domains.append(ScoredDomain(
                    domain=domain,
                    filter_status='FAIL',
                    filter_reason=f"Scoring error: {str(e)}",
                    total_meaning_score=None,
                    age_score=None,
                    lexical_frequency_score=None,
                    semantic_value_score=None,
                    rank=None
                ))
        
        # Sort by score (PASS domains first, then by score DESC)
        scored_domains.sort(key=lambda x: (
            x.filter_status != 'PASS',  # PASS first
            -(x.total_meaning_score or 0)  # Higher score first
        ))
        
        # Assign ranks
        rank = 1
        for scored in scored_domains:
            if scored.filter_status == 'PASS':
                scored.rank = rank
                rank += 1
        
        passed_count = sum(1 for s in scored_domains if s.filter_status == 'PASS')
        logger.info("Domain scoring complete", 
                   total=len(domains),
                   passed=passed_count,
                   failed=len(domains) - passed_count)
        
        return scored_domains


















