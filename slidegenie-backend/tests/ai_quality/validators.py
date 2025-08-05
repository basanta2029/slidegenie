"""
Academic Content Validators Module.

Provides validators for references, citations, and content integrity.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import structlog
from pydantic import BaseModel, Field, validator

from app.domain.schemas.generation import Citation

logger = structlog.get_logger(__name__)


class ReferenceValidator:
    """Validates academic references and citations."""
    
    def __init__(self):
        # Citation style patterns
        self.citation_styles = {
            "apa": {
                "pattern": r'([A-Z][a-z]+(?:\s+[A-Z]\.)?)(?:\s*,\s*[A-Z]\.\s*[A-Z]\.)?(?:\s+&\s+[A-Z][a-z]+(?:\s+[A-Z]\.)?)*\s*\((\d{4})\)\.\s*(.+?)\.\s*(.+?)(?:\s*,\s*(\d+)\((\d+)\))?\.',
                "format": "Author(s) (Year). Title. Source.",
                "example": "Smith, J. & Doe, A. (2023). Title of work. Journal Name, 10(2).",
            },
            "mla": {
                "pattern": r'([A-Z][a-z]+,\s*[A-Z][a-z]+)(?:\s+and\s+[A-Z][a-z]+,\s*[A-Z][a-z]+)*\.\s*"(.+?)"\s*(.+?),\s*(.+?)\s*\((\d{4})\)',
                "format": 'Last, First. "Title." Source, Publisher (Year).',
                "example": 'Smith, John. "Title of Article." Journal Name, vol. 10, no. 2 (2023).',
            },
            "chicago": {
                "pattern": r'([A-Z][a-z]+,\s*[A-Z][a-z]+)\.\s*"(.+?)"\s*(.+?)\s*(\d+),\s*no\.\s*(\d+)\s*\((\d{4})\)',
                "format": 'Last, First. "Title." Journal vol, no. num (Year).',
                "example": 'Smith, John. "Title of Article." Journal Name 10, no. 2 (2023).',
            },
            "ieee": {
                "pattern": r'\[(\d+)\]\s*([A-Z]\.\s*[A-Z][a-z]+)(?:\s+and\s+[A-Z]\.\s*[A-Z][a-z]+)*,\s*"(.+?),"\s*(.+?),\s*vol\.\s*(\d+),\s*no\.\s*(\d+),\s*pp\.\s*(\d+-\d+),\s*(\d{4})',
                "format": '[#] A. Author, "Title," Journal, vol. #, no. #, pp. #-#, Year.',
                "example": '[1] J. Smith, "Title," IEEE Trans., vol. 10, no. 2, pp. 123-456, 2023.',
            },
        }
        
        # Valid publication types
        self.publication_types = {
            "journal", "conference", "book", "thesis", "report",
            "website", "patent", "standard", "preprint"
        }
        
        # Academic databases for validation
        self.academic_databases = {
            "doi.org", "pubmed.ncbi.nlm.nih.gov", "arxiv.org",
            "ieeexplore.ieee.org", "dl.acm.org", "springer.com",
            "sciencedirect.com", "nature.com", "science.org"
        }
    
    def validate_reference(self, reference: Citation) -> Dict[str, Any]:
        """
        Validate a single reference.
        
        Args:
            reference: Citation object to validate
            
        Returns:
            Validation result with issues and suggestions
        """
        issues = []
        warnings = []
        
        # Check required fields
        if not reference.authors or not reference.authors[0]:
            issues.append({
                "field": "authors",
                "severity": "critical",
                "message": "Missing author information",
                "suggestion": "Add at least one author name"
            })
        
        if not reference.title:
            issues.append({
                "field": "title",
                "severity": "critical",
                "message": "Missing title",
                "suggestion": "Add the publication title"
            })
        
        if not reference.year:
            issues.append({
                "field": "year",
                "severity": "major",
                "message": "Missing publication year",
                "suggestion": "Add the year of publication"
            })
        
        # Validate specific fields
        if reference.authors:
            author_issues = self._validate_authors(reference.authors)
            issues.extend(author_issues)
        
        if reference.year:
            year_issues = self._validate_year(reference.year)
            issues.extend(year_issues)
        
        if reference.doi:
            doi_issues = self._validate_doi(reference.doi)
            issues.extend(doi_issues)
        
        if reference.url:
            url_issues = self._validate_url(reference.url)
            issues.extend(url_issues)
        
        # Check for completeness based on type
        if reference.type:
            completeness_issues = self._check_completeness(reference)
            warnings.extend(completeness_issues)
        
        # Determine citation style if formatted
        detected_style = self._detect_citation_style(reference)
        
        return {
            "valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
            "issues": issues,
            "warnings": warnings,
            "detected_style": detected_style,
            "completeness_score": self._calculate_completeness_score(reference),
        }
    
    def validate_citation_consistency(self, citations: List[Citation]) -> Dict[str, Any]:
        """
        Validate consistency across multiple citations.
        
        Args:
            citations: List of citations to check
            
        Returns:
            Consistency analysis results
        """
        if not citations:
            return {"consistent": True, "issues": []}
        
        issues = []
        
        # Check style consistency
        styles = []
        for citation in citations:
            style = self._detect_citation_style(citation)
            if style:
                styles.append(style)
        
        unique_styles = set(styles)
        if len(unique_styles) > 1:
            issues.append({
                "type": "style_inconsistency",
                "severity": "major",
                "message": f"Multiple citation styles detected: {', '.join(unique_styles)}",
                "suggestion": "Use a single citation style throughout"
            })
        
        # Check author name format consistency
        author_formats = self._analyze_author_formats(citations)
        if len(author_formats) > 1:
            issues.append({
                "type": "author_format_inconsistency",
                "severity": "minor",
                "message": "Inconsistent author name formats",
                "suggestion": "Use consistent format (e.g., 'Last, First' or 'First Last')"
            })
        
        # Check for duplicate citations
        duplicates = self._find_duplicate_citations(citations)
        if duplicates:
            issues.append({
                "type": "duplicate_citations",
                "severity": "major",
                "message": f"Found {len(duplicates)} duplicate citations",
                "suggestion": "Remove duplicate references",
                "duplicates": duplicates
            })
        
        return {
            "consistent": len(issues) == 0,
            "issues": issues,
            "style_distribution": dict(zip(unique_styles, [styles.count(s) for s in unique_styles])),
        }
    
    def _validate_authors(self, authors: List[str]) -> List[Dict[str, Any]]:
        """Validate author names."""
        issues = []
        
        for i, author in enumerate(authors):
            if not author or not author.strip():
                issues.append({
                    "field": f"authors[{i}]",
                    "severity": "major",
                    "message": "Empty author name",
                    "suggestion": "Remove empty author or add name"
                })
                continue
            
            # Check for common issues
            if len(author) < 3:
                issues.append({
                    "field": f"authors[{i}]",
                    "severity": "minor",
                    "message": f"Unusually short author name: '{author}'",
                    "suggestion": "Verify author name is complete"
                })
            
            if author.count(',') > 1:
                issues.append({
                    "field": f"authors[{i}]",
                    "severity": "minor",
                    "message": f"Multiple commas in author name: '{author}'",
                    "suggestion": "Use format 'Last, First' or 'First Last'"
                })
            
            # Check for et al. in individual author
            if "et al" in author.lower():
                issues.append({
                    "field": f"authors[{i}]",
                    "severity": "major",
                    "message": "'et al.' should not be in individual author names",
                    "suggestion": "List authors individually or use separate et_al field"
                })
        
        return issues
    
    def _validate_year(self, year: int) -> List[Dict[str, Any]]:
        """Validate publication year."""
        issues = []
        current_year = datetime.now().year
        
        if year > current_year:
            issues.append({
                "field": "year",
                "severity": "critical",
                "message": f"Future publication year: {year}",
                "suggestion": f"Year cannot be later than {current_year}"
            })
        elif year < 1450:  # Before printing press
            issues.append({
                "field": "year",
                "severity": "major",
                "message": f"Unusually old publication year: {year}",
                "suggestion": "Verify the publication year"
            })
        elif year < 1900:
            issues.append({
                "field": "year",
                "severity": "minor",
                "message": f"Historical publication: {year}",
                "suggestion": "Ensure historical date is accurate"
            })
        
        return issues
    
    def _validate_doi(self, doi: str) -> List[Dict[str, Any]]:
        """Validate DOI format."""
        issues = []
        
        # DOI pattern: 10.xxxx/xxxxx
        doi_pattern = r'^10\.\d{4,}(?:\.\d+)?/[-._;()/:\w]+$'
        
        if not re.match(doi_pattern, doi):
            issues.append({
                "field": "doi",
                "severity": "major",
                "message": f"Invalid DOI format: '{doi}'",
                "suggestion": "DOI should match pattern: 10.xxxx/xxxxx"
            })
        
        # Check for common DOI issues
        if doi.startswith('http'):
            issues.append({
                "field": "doi",
                "severity": "minor",
                "message": "DOI should not include URL prefix",
                "suggestion": "Remove 'http://doi.org/' prefix"
            })
        
        return issues
    
    def _validate_url(self, url: str) -> List[Dict[str, Any]]:
        """Validate URL format and accessibility."""
        issues = []
        
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                issues.append({
                    "field": "url",
                    "severity": "major",
                    "message": "URL missing protocol",
                    "suggestion": "Add 'http://' or 'https://' prefix"
                })
            elif parsed.scheme not in ['http', 'https']:
                issues.append({
                    "field": "url",
                    "severity": "minor",
                    "message": f"Unusual URL scheme: {parsed.scheme}",
                    "suggestion": "Use http or https for web URLs"
                })
            
            if not parsed.netloc:
                issues.append({
                    "field": "url",
                    "severity": "major",
                    "message": "URL missing domain",
                    "suggestion": "Include the complete URL with domain"
                })
            
            # Check if from academic source
            if parsed.netloc:
                is_academic = any(
                    domain in parsed.netloc 
                    for domain in self.academic_databases
                )
                if not is_academic and not any(
                    tld in parsed.netloc 
                    for tld in ['.edu', '.ac.', '.gov']
                ):
                    issues.append({
                        "field": "url",
                        "severity": "info",
                        "message": "Non-academic URL source",
                        "suggestion": "Prefer academic databases when available"
                    })
        
        except Exception as e:
            issues.append({
                "field": "url",
                "severity": "critical",
                "message": f"Invalid URL format: {str(e)}",
                "suggestion": "Provide a valid URL"
            })
        
        return issues
    
    def _check_completeness(self, reference: Citation) -> List[Dict[str, Any]]:
        """Check reference completeness based on type."""
        warnings = []
        
        required_fields = {
            "journal": ["authors", "title", "journal", "year", "volume"],
            "conference": ["authors", "title", "conference", "year"],
            "book": ["authors", "title", "publisher", "year"],
            "thesis": ["authors", "title", "institution", "year", "type"],
            "website": ["authors", "title", "url", "year"],
        }
        
        ref_type = reference.type or "journal"
        if ref_type in required_fields:
            for field in required_fields[ref_type]:
                if not getattr(reference, field, None):
                    warnings.append({
                        "field": field,
                        "severity": "warning",
                        "message": f"Missing recommended field for {ref_type}",
                        "suggestion": f"Add {field} for complete {ref_type} reference"
                    })
        
        return warnings
    
    def _detect_citation_style(self, citation: Citation) -> Optional[str]:
        """Detect the citation style used."""
        # This would need the formatted citation string
        # For now, return None as we're working with structured data
        return None
    
    def _calculate_completeness_score(self, reference: Citation) -> float:
        """Calculate how complete a reference is."""
        fields = [
            "authors", "title", "year", "journal", "volume", "issue",
            "pages", "doi", "url", "publisher"
        ]
        
        filled_fields = sum(1 for field in fields if getattr(reference, field, None))
        
        return filled_fields / len(fields)
    
    def _analyze_author_formats(self, citations: List[Citation]) -> Set[str]:
        """Analyze author name formats used."""
        formats = set()
        
        for citation in citations:
            if citation.authors:
                for author in citation.authors:
                    if ',' in author:
                        formats.add("last_first")
                    else:
                        formats.add("first_last")
        
        return formats
    
    def _find_duplicate_citations(self, citations: List[Citation]) -> List[Tuple[int, int]]:
        """Find duplicate citations."""
        duplicates = []
        
        for i in range(len(citations)):
            for j in range(i + 1, len(citations)):
                if self._are_citations_duplicate(citations[i], citations[j]):
                    duplicates.append((i, j))
        
        return duplicates
    
    def _are_citations_duplicate(self, cite1: Citation, cite2: Citation) -> bool:
        """Check if two citations are duplicates."""
        # Same DOI
        if cite1.doi and cite2.doi and cite1.doi == cite2.doi:
            return True
        
        # Same title and year
        if cite1.title and cite2.title:
            title_similarity = self._calculate_similarity(
                cite1.title.lower(), 
                cite2.title.lower()
            )
            if title_similarity > 0.9 and cite1.year == cite2.year:
                return True
        
        return False
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity (simple implementation)."""
        # Simple character-based similarity
        common = sum(1 for c1, c2 in zip(str1, str2) if c1 == c2)
        return common / max(len(str1), len(str2))


class ContentValidator:
    """Validates academic content integrity."""
    
    def __init__(self):
        # Academic content patterns
        self.claim_patterns = [
            r'studies\s+(?:show|indicate|suggest|demonstrate)',
            r'research\s+(?:shows|indicates|suggests|demonstrates)',
            r'evidence\s+(?:shows|indicates|suggests|demonstrates)',
            r'data\s+(?:show|indicate|suggest|demonstrate)',
            r'analysis\s+(?:reveals|shows|indicates)',
            r'findings\s+(?:suggest|indicate|show)',
            r'results\s+(?:demonstrate|indicate|show)',
        ]
        
        # Statistical patterns
        self.stat_patterns = {
            "percentage": r'(\d+(?:\.\d+)?)\s*%',
            "p_value": r'p\s*[<>=]\s*(0?\.\d+)',
            "confidence_interval": r'(\d+(?:\.\d+)?)\s*%\s*CI',
            "correlation": r'r\s*=\s*([+-]?0?\.\d+)',
            "sample_size": r'n\s*=\s*(\d+)',
            "mean_std": r'(\d+(?:\.\d+)?)\s*±\s*(\d+(?:\.\d+)?)',
            "range": r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',
        }
    
    def validate_content(self, content: str, references: List[Citation]) -> Dict[str, Any]:
        """
        Validate academic content.
        
        Args:
            content: Text content to validate
            references: Available references for citation checking
            
        Returns:
            Validation results
        """
        issues = []
        
        # Extract and validate claims
        claims = self._extract_claims(content)
        uncited_claims = self._find_uncited_claims(claims, content)
        
        if uncited_claims:
            issues.append({
                "type": "uncited_claims",
                "severity": "major",
                "count": len(uncited_claims),
                "message": f"{len(uncited_claims)} claims lack citations",
                "examples": uncited_claims[:3]
            })
        
        # Validate statistical claims
        stat_issues = self._validate_statistical_claims(content)
        issues.extend(stat_issues)
        
        # Check for plagiarism indicators
        plagiarism_indicators = self._check_plagiarism_indicators(content)
        if plagiarism_indicators:
            issues.append({
                "type": "potential_plagiarism",
                "severity": "critical",
                "indicators": plagiarism_indicators,
                "message": "Content shows potential plagiarism indicators"
            })
        
        # Check content coherence
        coherence_score = self._assess_coherence(content)
        if coherence_score < 0.6:
            issues.append({
                "type": "poor_coherence",
                "severity": "major",
                "score": coherence_score,
                "message": "Content lacks coherence and logical flow"
            })
        
        return {
            "valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
            "issues": issues,
            "metrics": {
                "claim_count": len(claims),
                "cited_claims": len(claims) - len(uncited_claims),
                "coherence_score": coherence_score,
                "statistical_claims": len(self._extract_statistics(content)),
            }
        }
    
    def _extract_claims(self, content: str) -> List[Dict[str, Any]]:
        """Extract academic claims from content."""
        claims = []
        
        for pattern in self.claim_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Extract surrounding sentence
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 100)
                sentence = content[start:end].strip()
                
                # Clean up sentence boundaries
                sentence = re.sub(r'^[^.!?]*?([A-Z])', r'\1', sentence)
                sentence = re.sub(r'([.!?])[^.!?]*$', r'\1', sentence)
                
                claims.append({
                    "text": sentence,
                    "position": match.start(),
                    "type": "research_claim"
                })
        
        return claims
    
    def _find_uncited_claims(self, claims: List[Dict[str, Any]], content: str) -> List[str]:
        """Find claims without citations."""
        uncited = []
        
        for claim in claims:
            # Check if citation follows within reasonable distance
            claim_end = claim["position"] + len(claim["text"])
            following_text = content[claim_end:claim_end + 50]
            
            # Look for citation patterns
            citation_patterns = [
                r'\[\d+\]',  # [1]
                r'\([A-Za-z]+(?:\s+et\s+al\.)?,?\s*\d{4}\)',  # (Author, 2023)
                r'\d+',  # Simple superscript number
            ]
            
            has_citation = any(
                re.search(pattern, following_text) 
                for pattern in citation_patterns
            )
            
            if not has_citation:
                uncited.append(claim["text"])
        
        return uncited
    
    def _validate_statistical_claims(self, content: str) -> List[Dict[str, Any]]:
        """Validate statistical claims in content."""
        issues = []
        
        for stat_type, pattern in self.stat_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                value = match.group(1)
                validation = self._validate_statistical_value(stat_type, value)
                
                if not validation["valid"]:
                    issues.append({
                        "type": "invalid_statistic",
                        "severity": validation["severity"],
                        "stat_type": stat_type,
                        "value": value,
                        "message": validation["message"],
                        "context": content[max(0, match.start()-30):match.end()+30]
                    })
        
        return issues
    
    def _validate_statistical_value(self, stat_type: str, value: str) -> Dict[str, Any]:
        """Validate a specific statistical value."""
        try:
            if stat_type == "percentage":
                val = float(value)
                if val > 100 or val < 0:
                    return {
                        "valid": False,
                        "severity": "critical",
                        "message": f"Percentage must be 0-100, got {val}"
                    }
            
            elif stat_type == "p_value":
                val = float(value)
                if val > 1 or val < 0:
                    return {
                        "valid": False,
                        "severity": "critical",
                        "message": f"P-value must be 0-1, got {val}"
                    }
            
            elif stat_type == "correlation":
                val = float(value)
                if abs(val) > 1:
                    return {
                        "valid": False,
                        "severity": "critical",
                        "message": f"Correlation must be -1 to 1, got {val}"
                    }
            
            elif stat_type == "confidence_interval":
                val = float(value)
                if val not in [90, 95, 99, 99.9]:
                    return {
                        "valid": False,
                        "severity": "minor",
                        "message": f"Unusual CI level: {val}%"
                    }
            
            return {"valid": True}
            
        except ValueError:
            return {
                "valid": False,
                "severity": "major",
                "message": f"Invalid numeric value: {value}"
            }
    
    def _check_plagiarism_indicators(self, content: str) -> List[str]:
        """Check for potential plagiarism indicators."""
        indicators = []
        
        # Check for inconsistent writing style
        sentences = re.split(r'[.!?]\s+', content)
        if len(sentences) > 5:
            # Simple style consistency check
            formal_count = sum(
                1 for s in sentences 
                if any(word in s.lower() for word in 
                      ["therefore", "moreover", "furthermore", "consequently"])
            )
            informal_count = sum(
                1 for s in sentences 
                if any(word in s.lower() for word in 
                      ["basically", "actually", "really", "stuff"])
            )
            
            if formal_count > 0 and informal_count > 0:
                ratio = formal_count / (formal_count + informal_count)
                if 0.3 < ratio < 0.7:
                    indicators.append("Inconsistent writing style")
        
        # Check for unusual quotation patterns
        if content.count('"') % 2 != 0:
            indicators.append("Unmatched quotation marks")
        
        # Check for suspicious formatting
        if '...' in content and content.count('...') > 2:
            indicators.append("Multiple ellipses suggesting omitted content")
        
        return indicators
    
    def _assess_coherence(self, content: str) -> float:
        """Assess content coherence."""
        if not content:
            return 0.0
        
        sentences = re.split(r'[.!?]\s+', content)
        if len(sentences) < 2:
            return 1.0
        
        coherence_score = 1.0
        
        # Check for transition words
        transition_words = [
            "however", "therefore", "moreover", "furthermore",
            "additionally", "consequently", "nevertheless",
            "thus", "hence", "accordingly", "similarly"
        ]
        
        transition_count = sum(
            1 for sentence in sentences[1:]
            if any(word in sentence.lower() for word in transition_words)
        )
        
        # Bonus for good transitions
        if transition_count > len(sentences) / 4:
            coherence_score += 0.1
        
        # Check for topic consistency
        # Simple word overlap between consecutive sentences
        for i in range(len(sentences) - 1):
            words1 = set(sentences[i].lower().split())
            words2 = set(sentences[i + 1].lower().split())
            
            if len(words1) > 5 and len(words2) > 5:
                overlap = len(words1.intersection(words2))
                if overlap < 2:  # Very little overlap
                    coherence_score -= 0.1
        
        return max(0.0, min(1.0, coherence_score))
    
    def _extract_statistics(self, content: str) -> List[Dict[str, Any]]:
        """Extract all statistical claims from content."""
        statistics = []
        
        for stat_type, pattern in self.stat_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                statistics.append({
                    "type": stat_type,
                    "value": match.group(0),
                    "position": match.start()
                })
        
        return statistics