"""
Academic Accuracy Testing Module.

Tests academic accuracy including fact checking, citation verification,
reference validation, and terminology consistency.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog
import requests
from fuzzywuzzy import fuzz

from app.domain.schemas.generation import Citation

logger = structlog.get_logger(__name__)


@dataclass
class AccuracyResult:
    """Result of academic accuracy assessment."""
    fact_accuracy_score: float
    citation_accuracy_score: float
    reference_validity_score: float
    terminology_consistency_score: float
    statistical_validity_score: float
    issues: List[Dict[str, Any]]
    verified_facts: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class AcademicAccuracyTest:
    """Tests academic accuracy of generated content."""
    
    def __init__(self):
        # Common academic databases for verification
        self.academic_databases = {
            "crossref": "https://api.crossref.org/works",
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            "arxiv": "http://export.arxiv.org/api/query",
        }
        
        # Statistical claim patterns
        self.statistical_patterns = {
            "percentage": r'(\d+(?:\.\d+)?)\s*%',
            "p_value": r'p\s*[<>=]\s*(0?\.\d+)',
            "correlation": r'r\s*=\s*([+-]?0?\.\d+)',
            "sample_size": r'n\s*=\s*(\d+)',
            "confidence_interval": r'(\d+(?:\.\d+)?)\s*%\s*CI',
            "mean_std": r'(\d+(?:\.\d+)?)\s*±\s*(\d+(?:\.\d+)?)',
        }
        
        # Academic terminology database
        self.terminology_db = {
            "methodology": ["quantitative", "qualitative", "mixed methods", "experimental", "observational"],
            "statistics": ["significant", "correlation", "regression", "variance", "hypothesis"],
            "research": ["systematic review", "meta-analysis", "randomized controlled trial", "cohort study"],
        }
    
    def assess(self, content: Dict[str, Any]) -> AccuracyResult:
        """
        Assess academic accuracy of content.
        
        Args:
            content: Content to assess including slides and references
            
        Returns:
            AccuracyResult with detailed assessment
        """
        slides = content.get("slides", [])
        references = content.get("references", [])
        
        # Perform accuracy checks
        fact_score, fact_issues, verified_facts = self._check_facts(slides)
        citation_score, citation_issues = self._check_citations(slides, references)
        reference_score, reference_issues = self._validate_references(references)
        terminology_score, terminology_issues = self._check_terminology(slides)
        statistical_score, statistical_issues = self._validate_statistics(slides)
        
        # Combine all issues
        all_issues = (
            fact_issues + citation_issues + reference_issues +
            terminology_issues + statistical_issues
        )
        
        return AccuracyResult(
            fact_accuracy_score=fact_score,
            citation_accuracy_score=citation_score,
            reference_validity_score=reference_score,
            terminology_consistency_score=terminology_score,
            statistical_validity_score=statistical_score,
            issues=all_issues,
            verified_facts=verified_facts,
            metadata={
                "total_claims": len(self._extract_claims(slides)),
                "verified_references": self._count_verified_references(reference_issues),
                "statistical_claims": len(self._extract_statistical_claims(slides)),
            }
        )
    
    def _check_facts(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Check factual accuracy of claims."""
        issues = []
        verified_facts = []
        claims = self._extract_claims(slides)
        
        if not claims:
            return 1.0, [], []
        
        verified_count = 0
        
        for claim in claims:
            # Attempt to verify claim
            verification_result = self._verify_claim(claim)
            
            if verification_result["verified"]:
                verified_count += 1
                verified_facts.append({
                    "claim": claim["text"],
                    "source": verification_result["source"],
                    "confidence": verification_result["confidence"],
                })
            else:
                issues.append({
                    "type": "unverified_fact",
                    "severity": "major",
                    "slide_number": claim["slide_number"],
                    "description": f"Unable to verify claim: {claim['text'][:100]}...",
                    "suggestion": "Add citation or verify accuracy",
                })
        
        fact_score = verified_count / len(claims) if claims else 1.0
        
        return fact_score, issues, verified_facts
    
    def _check_citations(self, slides: List[Dict[str, Any]], references: List[Citation]) -> Tuple[float, List[Dict[str, Any]]]:
        """Check citation accuracy and completeness."""
        issues = []
        
        # Extract all citation markers from slides
        citation_markers = self._extract_citation_markers(slides)
        
        # Check if all citations have corresponding references
        reference_ids = {ref.id for ref in references if ref.id}
        missing_references = citation_markers - reference_ids
        
        for missing_ref in missing_references:
            issues.append({
                "type": "missing_reference",
                "severity": "critical",
                "description": f"Citation [{missing_ref}] has no corresponding reference",
                "suggestion": "Add missing reference to bibliography",
            })
        
        # Check for uncited references
        cited_refs = self._extract_cited_references(slides)
        all_ref_ids = {ref.id for ref in references if ref.id}
        uncited_refs = all_ref_ids - cited_refs
        
        for uncited in uncited_refs:
            issues.append({
                "type": "uncited_reference",
                "severity": "minor",
                "description": f"Reference [{uncited}] is not cited in presentation",
                "suggestion": "Remove unused reference or add citation",
            })
        
        # Check citation format consistency
        formats = self._analyze_citation_formats(slides)
        if len(formats) > 1:
            issues.append({
                "type": "inconsistent_citation_format",
                "severity": "major",
                "description": f"Multiple citation formats detected: {', '.join(formats)}",
                "suggestion": "Use consistent citation format throughout",
            })
        
        # Calculate score
        total_issues = len(missing_references) + len(uncited_refs)
        total_citations = len(citation_markers) + len(all_ref_ids)
        
        citation_score = 1.0 - (total_issues / total_citations) if total_citations > 0 else 1.0
        
        return max(0.0, citation_score), issues
    
    def _validate_references(self, references: List[Citation]) -> Tuple[float, List[Dict[str, Any]]]:
        """Validate reference accuracy and format."""
        issues = []
        valid_count = 0
        
        for i, ref in enumerate(references):
            validation_result = self._validate_single_reference(ref)
            
            if validation_result["valid"]:
                valid_count += 1
            else:
                for issue in validation_result["issues"]:
                    issues.append({
                        "type": "invalid_reference",
                        "severity": issue["severity"],
                        "reference_number": i + 1,
                        "description": issue["description"],
                        "suggestion": issue["suggestion"],
                    })
        
        reference_score = valid_count / len(references) if references else 1.0
        
        return reference_score, issues
    
    def _check_terminology(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]]]:
        """Check terminology consistency and accuracy."""
        issues = []
        
        # Extract all technical terms
        terms = self._extract_technical_terms(slides)
        
        # Check for consistency
        term_variations = self._find_terminology_variations(terms)
        
        for canonical, variations in term_variations.items():
            if len(variations) > 1:
                issues.append({
                    "type": "inconsistent_terminology",
                    "severity": "minor",
                    "description": f"Inconsistent use of term: {', '.join(variations)}",
                    "suggestion": f"Use consistent terminology: '{canonical}'",
                })
        
        # Check for incorrect usage
        misused_terms = self._check_term_usage(slides)
        for misuse in misused_terms:
            issues.append({
                "type": "incorrect_terminology",
                "severity": "major",
                "slide_number": misuse["slide_number"],
                "description": f"Potentially incorrect use of '{misuse['term']}'",
                "suggestion": misuse["suggestion"],
            })
        
        # Calculate score
        total_terms = len(terms)
        issue_count = len(term_variations) + len(misused_terms)
        
        terminology_score = 1.0 - (issue_count / total_terms) if total_terms > 0 else 1.0
        
        return max(0.0, terminology_score), issues
    
    def _validate_statistics(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]]]:
        """Validate statistical claims and values."""
        issues = []
        statistical_claims = self._extract_statistical_claims(slides)
        
        valid_count = 0
        
        for claim in statistical_claims:
            validation = self._validate_statistical_claim(claim)
            
            if validation["valid"]:
                valid_count += 1
            else:
                issues.append({
                    "type": "invalid_statistics",
                    "severity": validation["severity"],
                    "slide_number": claim["slide_number"],
                    "description": validation["description"],
                    "suggestion": validation["suggestion"],
                })
        
        statistical_score = valid_count / len(statistical_claims) if statistical_claims else 1.0
        
        return statistical_score, issues
    
    def _extract_claims(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract factual claims from slides."""
        claims = []
        
        claim_indicators = [
            "research shows", "studies indicate", "evidence suggests",
            "it has been found", "data demonstrates", "analysis reveals",
            "experiments confirm", "observations show", "results indicate"
        ]
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            # Look for sentences with claim indicators
            sentences = re.split(r'[.!?]\s*', content)
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(indicator in sentence_lower for indicator in claim_indicators):
                    claims.append({
                        "text": sentence.strip(),
                        "slide_number": i + 1,
                        "type": "research_claim"
                    })
            
            # Look for quantitative claims
            if re.search(r'\d+\.?\d*\s*%', content):
                claims.append({
                    "text": content,
                    "slide_number": i + 1,
                    "type": "quantitative_claim"
                })
        
        return claims
    
    def _verify_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to verify a factual claim."""
        # This is a simplified verification process
        # In production, this would query academic databases
        
        confidence = 0.0
        source = None
        
        # Check for common verifiable patterns
        if "peer-reviewed" in claim["text"].lower():
            confidence = 0.8
            source = "academic_standard"
        elif re.search(r'\d{4}', claim["text"]):  # Has year reference
            confidence = 0.6
            source = "temporal_reference"
        elif any(term in claim["text"].lower() for term in ["meta-analysis", "systematic review"]):
            confidence = 0.9
            source = "high_quality_study"
        
        return {
            "verified": confidence > 0.5,
            "confidence": confidence,
            "source": source,
        }
    
    def _extract_citation_markers(self, slides: List[Dict[str, Any]]) -> Set[str]:
        """Extract all citation markers from slides."""
        markers = set()
        
        patterns = [
            r'\[(\d+)\]',  # [1]
            r'\(([A-Za-z]+(?:\s+(?:et\s+al\.|and\s+[A-Za-z]+))?,\s*\d{4})\)',  # (Author, 2023)
            r'([A-Za-z]+(?:\s+(?:et\s+al\.|and\s+[A-Za-z]+))?)\s+\(\d{4}\)',  # Author (2023)
        ]
        
        for slide in slides:
            content = self._get_slide_content(slide)
            for pattern in patterns:
                matches = re.findall(pattern, content)
                markers.update(matches)
        
        return markers
    
    def _extract_cited_references(self, slides: List[Dict[str, Any]]) -> Set[str]:
        """Extract references that are actually cited."""
        cited = set()
        
        for slide in slides:
            content = self._get_slide_content(slide)
            
            # Extract numbered citations
            numbered = re.findall(r'\[(\d+)\]', content)
            cited.update(numbered)
            
            # Extract author-year citations
            author_year = re.findall(r'\(([A-Za-z]+(?:\s+et\s+al\.)?),\s*(\d{4})\)', content)
            for author, year in author_year:
                cited.add(f"{author}_{year}")
        
        return cited
    
    def _analyze_citation_formats(self, slides: List[Dict[str, Any]]) -> List[str]:
        """Identify citation formats used."""
        formats = set()
        
        for slide in slides:
            content = self._get_slide_content(slide)
            
            if re.search(r'\[\d+\]', content):
                formats.add("numbered")
            if re.search(r'\([A-Za-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)', content):
                formats.add("author-year")
            if re.search(r'[A-Za-z]+\s+\(\d{4}\)', content):
                formats.add("author_(year)")
        
        return list(formats)
    
    def _validate_single_reference(self, reference: Citation) -> Dict[str, Any]:
        """Validate a single reference."""
        issues = []
        
        # Check required fields
        if not reference.authors or not reference.authors[0]:
            issues.append({
                "severity": "critical",
                "description": "Missing author information",
                "suggestion": "Add at least one author",
            })
        
        if not reference.title:
            issues.append({
                "severity": "critical",
                "description": "Missing title",
                "suggestion": "Add publication title",
            })
        
        if not reference.year:
            issues.append({
                "severity": "major",
                "description": "Missing publication year",
                "suggestion": "Add year of publication",
            })
        
        # Validate year
        if reference.year:
            current_year = datetime.now().year
            if reference.year > current_year:
                issues.append({
                    "severity": "critical",
                    "description": f"Future publication year: {reference.year}",
                    "suggestion": "Correct the publication year",
                })
            elif reference.year < 1900:
                issues.append({
                    "severity": "major",
                    "description": f"Unusually old publication year: {reference.year}",
                    "suggestion": "Verify the publication year",
                })
        
        # Check DOI format if provided
        if reference.doi:
            if not re.match(r'^10\.\d{4,}/[-._;()/:\w]+$', reference.doi):
                issues.append({
                    "severity": "minor",
                    "description": "Invalid DOI format",
                    "suggestion": "Use standard DOI format (10.xxxx/xxxxx)",
                })
        
        # Check URL format if provided
        if reference.url:
            if not re.match(r'^https?://', reference.url):
                issues.append({
                    "severity": "minor",
                    "description": "URL should start with http:// or https://",
                    "suggestion": "Add proper URL protocol",
                })
        
        return {
            "valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
            "issues": issues,
        }
    
    def _extract_technical_terms(self, slides: List[Dict[str, Any]]) -> List[str]:
        """Extract technical and academic terms."""
        terms = []
        
        # Patterns for technical terms
        patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',  # Multi-word proper nouns
            r'\b\w+(?:ology|ometry|ography|analysis|thesis)\b',  # Academic suffixes
            r'\b(?:meta-|quasi-|pseudo-|neo-|post-)\w+\b',  # Academic prefixes
        ]
        
        for slide in slides:
            content = self._get_slide_content(slide)
            for pattern in patterns:
                matches = re.findall(pattern, content)
                terms.extend(matches)
        
        # Add known academic terms found in content
        for category, term_list in self.terminology_db.items():
            for term in term_list:
                if any(term in slide_content.lower() for slide_content in 
                      [self._get_slide_content(s) for s in slides]):
                    terms.append(term)
        
        return terms
    
    def _find_terminology_variations(self, terms: List[str]) -> Dict[str, List[str]]:
        """Find variations of the same term."""
        variations = {}
        processed = set()
        
        for term in terms:
            if term.lower() in processed:
                continue
            
            similar_terms = []
            for other_term in terms:
                if term != other_term and fuzz.ratio(term.lower(), other_term.lower()) > 85:
                    similar_terms.append(other_term)
                    processed.add(other_term.lower())
            
            if similar_terms:
                variations[term] = [term] + similar_terms
                processed.add(term.lower())
        
        return variations
    
    def _check_term_usage(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for incorrect term usage."""
        misused = []
        
        # Common misuses in academic writing
        misuse_patterns = {
            r'\bdata\s+is\b': {
                "term": "data is",
                "suggestion": "Use 'data are' (data is plural)",
            },
            r'\bimpact\s+on\b': {
                "term": "impact on",
                "suggestion": "Consider 'effect on' or 'influence on' for clarity",
            },
            r'\bprove[sd]?\b': {
                "term": "prove/proved",
                "suggestion": "Use 'demonstrate', 'support', or 'suggest' instead",
            },
        }
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            for pattern, info in misuse_patterns.items():
                if re.search(pattern, content, re.I):
                    misused.append({
                        "slide_number": i + 1,
                        "term": info["term"],
                        "suggestion": info["suggestion"],
                    })
        
        return misused
    
    def _extract_statistical_claims(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract statistical claims from slides."""
        claims = []
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            for stat_type, pattern in self.statistical_patterns.items():
                matches = re.findall(pattern, content, re.I)
                for match in matches:
                    claims.append({
                        "type": stat_type,
                        "value": match,
                        "slide_number": i + 1,
                        "context": content,
                    })
        
        return claims
    
    def _validate_statistical_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a statistical claim."""
        stat_type = claim["type"]
        value = claim["value"]
        
        if stat_type == "percentage":
            val = float(value)
            if val > 100 or val < 0:
                return {
                    "valid": False,
                    "severity": "critical",
                    "description": f"Invalid percentage: {val}%",
                    "suggestion": "Percentages must be between 0 and 100",
                }
        
        elif stat_type == "p_value":
            val = float(value)
            if val > 1 or val < 0:
                return {
                    "valid": False,
                    "severity": "critical",
                    "description": f"Invalid p-value: {val}",
                    "suggestion": "P-values must be between 0 and 1",
                }
        
        elif stat_type == "correlation":
            val = float(value)
            if abs(val) > 1:
                return {
                    "valid": False,
                    "severity": "critical",
                    "description": f"Invalid correlation coefficient: {val}",
                    "suggestion": "Correlation coefficients must be between -1 and 1",
                }
        
        elif stat_type == "confidence_interval":
            val = float(value)
            if val not in [90, 95, 99, 99.9]:
                return {
                    "valid": False,
                    "severity": "minor",
                    "description": f"Unusual confidence interval: {val}%",
                    "suggestion": "Common CIs are 90%, 95%, or 99%",
                }
        
        return {"valid": True}
    
    def _get_slide_content(self, slide: Dict[str, Any]) -> str:
        """Extract all text content from a slide."""
        parts = []
        
        for key in ["title", "content", "bullet_points", "speaker_notes"]:
            if key in slide:
                if isinstance(slide[key], list):
                    parts.extend(slide[key])
                else:
                    parts.append(str(slide[key]))
        
        return " ".join(parts)
    
    def _count_verified_references(self, reference_issues: List[Dict[str, Any]]) -> int:
        """Count how many references were successfully verified."""
        # Count references without critical issues
        critical_refs = set()
        for issue in reference_issues:
            if issue.get("severity") == "critical" and "reference_number" in issue:
                critical_refs.add(issue["reference_number"])
        
        return len(reference_issues) - len(critical_refs)