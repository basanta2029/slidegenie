"""
Output Quality Validation Module.

Validates the quality of AI-generated slide content including coherence,
grammar, academic tone, visual balance, and consistency.
"""
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import structlog
from textstat import flesch_reading_ease, flesch_kincaid_grade
import language_tool_python

from app.domain.schemas.presentation import SlideResponse
from app.services.slides.quality.base import QualityIssue, QualityDimension

logger = structlog.get_logger(__name__)


@dataclass
class ContentQualityMetrics:
    """Metrics for content quality assessment."""
    coherence_score: float
    grammar_score: float
    academic_tone_score: float
    visual_balance_score: float
    consistency_score: float
    readability_score: float
    issues: List[QualityIssue]
    metadata: Dict[str, Any]


class OutputQualityValidator:
    """Validates the quality of AI-generated output."""
    
    def __init__(self):
        # Initialize grammar checker
        try:
            self.grammar_tool = language_tool_python.LanguageToolPublicAPI('en-US')
        except:
            logger.warning("LanguageTool not available, using basic grammar checks")
            self.grammar_tool = None
        
        # Academic tone indicators
        self.academic_indicators = {
            "formal_words": [
                "demonstrate", "indicate", "suggest", "illustrate", "examine",
                "analyze", "evaluate", "investigate", "hypothesis", "methodology",
                "significant", "correlation", "framework", "paradigm", "empirical"
            ],
            "informal_words": [
                "stuff", "things", "a lot", "very", "really", "basically",
                "actually", "just", "get", "got", "pretty", "kind of", "sort of"
            ],
            "first_person": r'\b(I|me|my|mine|we|us|our|ours)\b',
            "contractions": r"\b\w+'\w+\b",
            "passive_voice": r'\b(was|were|been|being|is|are|be)\s+\w+ed\b',
        }
        
        # Visual balance criteria
        self.visual_balance_criteria = {
            "max_bullet_points": 7,
            "optimal_bullet_points": (3, 5),
            "max_text_length": 150,  # characters per bullet
            "optimal_text_ratio": 0.4,  # text to slide area ratio
            "min_spacing": 0.1,  # minimum spacing ratio
        }
    
    def validate(self, content: Dict[str, Any]) -> ContentQualityMetrics:
        """
        Validate output quality.
        
        Args:
            content: Generated content including slides
            
        Returns:
            ContentQualityMetrics with detailed assessment
        """
        slides = content.get("slides", [])
        
        # Perform quality checks
        coherence_score, coherence_issues = self._check_coherence(slides)
        grammar_score, grammar_issues = self._check_grammar(slides)
        tone_score, tone_issues = self._check_academic_tone(slides)
        balance_score, balance_issues = self._check_visual_balance(slides)
        consistency_score, consistency_issues = self._check_consistency(slides)
        readability_score, readability_issues = self._check_readability(slides)
        
        # Combine all issues
        all_issues = (
            coherence_issues + grammar_issues + tone_issues +
            balance_issues + consistency_issues + readability_issues
        )
        
        return ContentQualityMetrics(
            coherence_score=coherence_score,
            grammar_score=grammar_score,
            academic_tone_score=tone_score,
            visual_balance_score=balance_score,
            consistency_score=consistency_score,
            readability_score=readability_score,
            issues=all_issues,
            metadata={
                "slide_count": len(slides),
                "avg_text_length": self._calculate_avg_text_length(slides),
                "vocabulary_diversity": self._calculate_vocabulary_diversity(slides),
            }
        )
    
    def _check_coherence(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[QualityIssue]]:
        """Check content coherence across slides."""
        if not slides:
            return 0.0, []
        
        issues = []
        coherence_score = 1.0
        
        # Check logical flow
        transition_words = [
            "therefore", "however", "moreover", "furthermore", "consequently",
            "additionally", "nevertheless", "thus", "hence", "accordingly"
        ]
        
        transition_count = 0
        for i, slide in enumerate(slides):
            content = self._extract_slide_text(slide)
            
            # Check for transition words
            for word in transition_words:
                if word in content.lower():
                    transition_count += 1
            
            # Check for abrupt topic changes
            if i > 0:
                prev_content = self._extract_slide_text(slides[i-1])
                similarity = self._calculate_text_similarity(prev_content, content)
                
                if similarity < 0.1:  # Very low similarity
                    issues.append(QualityIssue(
                        dimension=QualityDimension.COHERENCE,
                        severity="major",
                        slide_number=i + 1,
                        description=f"Abrupt topic change from slide {i} to {i+1}",
                        suggestion="Add transitional content or reorder slides"
                    ))
                    coherence_score -= 0.1
        
        # Check for logical structure
        expected_sections = ["introduction", "background", "method", "results", "conclusion"]
        found_sections = []
        
        for slide in slides:
            title = slide.get("title", "").lower()
            for section in expected_sections:
                if section in title:
                    found_sections.append(section)
        
        missing_sections = set(expected_sections[:3]) - set(found_sections)  # First 3 are essential
        if missing_sections:
            coherence_score -= len(missing_sections) * 0.1
            issues.append(QualityIssue(
                dimension=QualityDimension.COHERENCE,
                severity="major",
                description=f"Missing essential sections: {', '.join(missing_sections)}",
                suggestion="Add missing sections for complete presentation structure"
            ))
        
        # Bonus for good transitions
        if transition_count >= len(slides) // 2:
            coherence_score += 0.1
        
        return max(0.0, min(coherence_score, 1.0)), issues
    
    def _check_grammar(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[QualityIssue]]:
        """Check grammar and spelling."""
        if not slides:
            return 0.0, []
        
        issues = []
        total_errors = 0
        total_text_length = 0
        
        for i, slide in enumerate(slides):
            content = self._extract_slide_text(slide)
            total_text_length += len(content)
            
            if self.grammar_tool:
                # Use LanguageTool for comprehensive grammar checking
                try:
                    matches = self.grammar_tool.check(content)
                    for match in matches:
                        if match.ruleIssueType in ["grammar", "typo"]:
                            total_errors += 1
                            issues.append(QualityIssue(
                                dimension=QualityDimension.READABILITY,
                                severity="minor",
                                slide_number=i + 1,
                                description=f"{match.message}: '{match.context}'",
                                suggestion=match.replacements[0] if match.replacements else "Review this text"
                            ))
                except Exception as e:
                    logger.error(f"Grammar check failed: {e}")
            else:
                # Basic grammar checks
                errors = self._basic_grammar_check(content)
                total_errors += len(errors)
                for error in errors:
                    issues.append(QualityIssue(
                        dimension=QualityDimension.READABILITY,
                        severity="minor",
                        slide_number=i + 1,
                        description=error["description"],
                        suggestion=error["suggestion"]
                    ))
        
        # Calculate score based on error density
        if total_text_length > 0:
            error_rate = total_errors / (total_text_length / 100)  # Errors per 100 characters
            grammar_score = max(0.0, 1.0 - (error_rate * 0.1))
        else:
            grammar_score = 1.0
        
        return grammar_score, issues
    
    def _check_academic_tone(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[QualityIssue]]:
        """Check for appropriate academic tone."""
        if not slides:
            return 0.0, []
        
        issues = []
        tone_score = 1.0
        
        formal_count = 0
        informal_count = 0
        first_person_count = 0
        contraction_count = 0
        passive_voice_count = 0
        
        for i, slide in enumerate(slides):
            content = self._extract_slide_text(slide)
            content_lower = content.lower()
            
            # Count formal vs informal language
            for word in self.academic_indicators["formal_words"]:
                if word in content_lower:
                    formal_count += 1
            
            for word in self.academic_indicators["informal_words"]:
                if word in content_lower:
                    informal_count += 1
                    issues.append(QualityIssue(
                        dimension=QualityDimension.READABILITY,
                        severity="minor",
                        slide_number=i + 1,
                        description=f"Informal language detected: '{word}'",
                        suggestion="Use more formal academic language"
                    ))
            
            # Check for first person usage
            first_person_matches = re.findall(self.academic_indicators["first_person"], content)
            if first_person_matches:
                first_person_count += len(first_person_matches)
                issues.append(QualityIssue(
                    dimension=QualityDimension.READABILITY,
                    severity="minor",
                    slide_number=i + 1,
                    description="First-person pronouns detected",
                    suggestion="Use third-person perspective for academic presentations"
                ))
            
            # Check for contractions
            contractions = re.findall(self.academic_indicators["contractions"], content)
            if contractions:
                contraction_count += len(contractions)
                issues.append(QualityIssue(
                    dimension=QualityDimension.READABILITY,
                    severity="minor",
                    slide_number=i + 1,
                    description=f"Contractions detected: {', '.join(contractions[:3])}",
                    suggestion="Expand contractions for formal writing"
                ))
            
            # Check for passive voice (academic writing often uses it appropriately)
            passive_matches = re.findall(self.academic_indicators["passive_voice"], content)
            passive_voice_count += len(passive_matches)
        
        # Calculate tone score
        if formal_count + informal_count > 0:
            formality_ratio = formal_count / (formal_count + informal_count)
            tone_score = formality_ratio
        
        # Penalties for inappropriate language
        tone_score -= (first_person_count * 0.02)
        tone_score -= (contraction_count * 0.01)
        tone_score -= (informal_count * 0.03)
        
        # Passive voice is acceptable in academic writing
        if passive_voice_count > 0:
            tone_score += 0.05
        
        return max(0.0, min(tone_score, 1.0)), issues
    
    def _check_visual_balance(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[QualityIssue]]:
        """Check visual balance of slides."""
        if not slides:
            return 0.0, []
        
        issues = []
        balance_scores = []
        
        for i, slide in enumerate(slides):
            slide_score = 1.0
            
            # Check bullet points
            bullet_count = len(slide.get("bullet_points", []))
            if bullet_count > self.visual_balance_criteria["max_bullet_points"]:
                slide_score -= 0.2
                issues.append(QualityIssue(
                    dimension=QualityDimension.VISUAL_BALANCE,
                    severity="major",
                    slide_number=i + 1,
                    description=f"Too many bullet points ({bullet_count})",
                    suggestion=f"Reduce to {self.visual_balance_criteria['optimal_bullet_points'][1]} or fewer"
                ))
            elif bullet_count < self.visual_balance_criteria["optimal_bullet_points"][0]:
                slide_score -= 0.1
                issues.append(QualityIssue(
                    dimension=QualityDimension.VISUAL_BALANCE,
                    severity="minor",
                    slide_number=i + 1,
                    description=f"Too few bullet points ({bullet_count})",
                    suggestion="Add more content or merge with adjacent slide"
                ))
            
            # Check text length
            for j, bullet in enumerate(slide.get("bullet_points", [])):
                if len(bullet) > self.visual_balance_criteria["max_text_length"]:
                    slide_score -= 0.1
                    issues.append(QualityIssue(
                        dimension=QualityDimension.VISUAL_BALANCE,
                        severity="minor",
                        slide_number=i + 1,
                        description=f"Bullet point {j+1} is too long",
                        suggestion="Break into multiple points or simplify"
                    ))
            
            # Check for visual elements
            has_visual = any([
                slide.get("has_figure"),
                slide.get("has_table"),
                slide.get("has_equation"),
                slide.get("has_chart")
            ])
            
            # Data-heavy slides should have visuals
            if self._is_data_heavy(slide) and not has_visual:
                slide_score -= 0.15
                issues.append(QualityIssue(
                    dimension=QualityDimension.VISUAL_BALANCE,
                    severity="major",
                    slide_number=i + 1,
                    description="Data-heavy slide lacks visual elements",
                    suggestion="Add chart, table, or figure to visualize data"
                ))
            
            balance_scores.append(slide_score)
        
        return max(0.0, min(sum(balance_scores) / len(balance_scores), 1.0)), issues
    
    def _check_consistency(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[QualityIssue]]:
        """Check consistency across slides."""
        if not slides:
            return 0.0, []
        
        issues = []
        consistency_score = 1.0
        
        # Check title formatting consistency
        title_formats = []
        for slide in slides:
            title = slide.get("title", "")
            format_features = {
                "capitalized": title.istitle(),
                "all_caps": title.isupper(),
                "sentence_case": title[0].isupper() and title[1:].islower() if len(title) > 1 else False,
                "has_colon": ":" in title,
                "has_number": any(c.isdigit() for c in title)
            }
            title_formats.append(format_features)
        
        # Check if formats are consistent
        if len(set(str(f) for f in title_formats)) > 2:  # Allow some variation
            consistency_score -= 0.1
            issues.append(QualityIssue(
                dimension=QualityDimension.COHERENCE,
                severity="minor",
                description="Inconsistent title formatting across slides",
                suggestion="Use consistent capitalization and formatting for all titles"
            ))
        
        # Check terminology consistency
        terms = self._extract_key_terms(slides)
        term_variations = self._find_term_variations(terms)
        
        for term, variations in term_variations.items():
            if len(variations) > 1:
                consistency_score -= 0.05
                issues.append(QualityIssue(
                    dimension=QualityDimension.COHERENCE,
                    severity="minor",
                    description=f"Inconsistent terminology: {', '.join(variations)}",
                    suggestion=f"Use consistent term throughout: '{term}'"
                ))
        
        # Check citation format consistency
        citation_formats = self._analyze_citation_formats(slides)
        if len(citation_formats) > 1:
            consistency_score -= 0.1
            issues.append(QualityIssue(
                dimension=QualityDimension.CITATIONS,
                severity="major",
                description="Inconsistent citation formats detected",
                suggestion="Use a single citation format throughout (e.g., APA, MLA)"
            ))
        
        return max(0.0, min(consistency_score, 1.0)), issues
    
    def _check_readability(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[QualityIssue]]:
        """Check readability of slide content."""
        if not slides:
            return 0.0, []
        
        issues = []
        readability_scores = []
        
        for i, slide in enumerate(slides):
            content = self._extract_slide_text(slide)
            
            if len(content) > 50:  # Need sufficient text for analysis
                # Calculate readability scores
                try:
                    flesch_score = flesch_reading_ease(content)
                    grade_level = flesch_kincaid_grade(content)
                    
                    # Academic content should be readable but not too simple
                    if flesch_score < 30:  # Very difficult
                        issues.append(QualityIssue(
                            dimension=QualityDimension.READABILITY,
                            severity="major",
                            slide_number=i + 1,
                            description=f"Content is very difficult to read (Flesch score: {flesch_score:.1f})",
                            suggestion="Simplify sentence structure and use clearer language"
                        ))
                        readability_scores.append(0.5)
                    elif flesch_score > 80:  # Very easy
                        issues.append(QualityIssue(
                            dimension=QualityDimension.READABILITY,
                            severity="minor",
                            slide_number=i + 1,
                            description=f"Content may be too simple for academic presentation",
                            suggestion="Use more sophisticated vocabulary where appropriate"
                        ))
                        readability_scores.append(0.8)
                    else:
                        # Optimal range for academic content: 30-60
                        normalized_score = min(1.0, (flesch_score - 30) / 30 + 0.5)
                        readability_scores.append(normalized_score)
                    
                    # Check grade level
                    if grade_level > 16:  # Post-graduate level
                        issues.append(QualityIssue(
                            dimension=QualityDimension.READABILITY,
                            severity="minor",
                            slide_number=i + 1,
                            description=f"Content requires post-graduate reading level ({grade_level:.1f})",
                            suggestion="Consider your audience and simplify if needed"
                        ))
                except:
                    readability_scores.append(0.7)  # Default if calculation fails
            else:
                readability_scores.append(1.0)  # Short content is typically readable
        
        avg_readability = sum(readability_scores) / len(readability_scores) if readability_scores else 0.5
        
        return avg_readability, issues
    
    def _extract_slide_text(self, slide: Dict[str, Any]) -> str:
        """Extract all text from a slide."""
        parts = []
        
        if "title" in slide:
            parts.append(slide["title"])
        
        if "content" in slide:
            parts.append(slide["content"])
        
        if "bullet_points" in slide:
            parts.extend(slide["bullet_points"])
        
        if "speaker_notes" in slide:
            parts.append(slide["speaker_notes"])
        
        return " ".join(str(part) for part in parts if part)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _basic_grammar_check(self, text: str) -> List[Dict[str, str]]:
        """Perform basic grammar checks when LanguageTool is not available."""
        errors = []
        
        # Check for double spaces
        if "  " in text:
            errors.append({
                "description": "Double spaces detected",
                "suggestion": "Use single spaces between words"
            })
        
        # Check for missing space after punctuation
        if re.search(r'[.!?][a-zA-Z]', text):
            errors.append({
                "description": "Missing space after punctuation",
                "suggestion": "Add space after periods, exclamation marks, and question marks"
            })
        
        # Check for repeated words
        repeated = re.findall(r'\b(\w+)\s+\1\b', text, re.I)
        if repeated:
            errors.append({
                "description": f"Repeated words: {', '.join(set(repeated))}",
                "suggestion": "Remove duplicate words"
            })
        
        return errors
    
    def _calculate_avg_text_length(self, slides: List[Dict[str, Any]]) -> float:
        """Calculate average text length per slide."""
        if not slides:
            return 0.0
        
        total_length = sum(len(self._extract_slide_text(slide)) for slide in slides)
        return total_length / len(slides)
    
    def _calculate_vocabulary_diversity(self, slides: List[Dict[str, Any]]) -> float:
        """Calculate vocabulary diversity (type-token ratio)."""
        all_words = []
        
        for slide in slides:
            text = self._extract_slide_text(slide).lower()
            words = re.findall(r'\b\w+\b', text)
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        unique_words = set(all_words)
        return len(unique_words) / len(all_words)
    
    def _is_data_heavy(self, slide: Dict[str, Any]) -> bool:
        """Check if slide contains significant data."""
        content = self._extract_slide_text(slide)
        
        # Check for numbers, percentages, statistics
        data_patterns = [
            r'\d+\.?\d*%',  # Percentages
            r'\bp\s*[<>=]\s*0\.\d+',  # p-values
            r'\bn\s*=\s*\d+',  # sample sizes
            r'\d+\.?\d*\s*±\s*\d+\.?\d*',  # mean ± std
            r'correlation|regression|significant|analysis',  # Statistical terms
        ]
        
        data_count = sum(len(re.findall(pattern, content, re.I)) for pattern in data_patterns)
        
        return data_count >= 3
    
    def _extract_key_terms(self, slides: List[Dict[str, Any]]) -> List[str]:
        """Extract key terms from slides."""
        terms = []
        
        # Common academic terms to look for
        term_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',  # Multi-word proper nouns
            r'\b\w+(?:tion|ment|ity|ness|ism|ogy|phy)\b',  # Academic suffixes
        ]
        
        for slide in slides:
            content = self._extract_slide_text(slide)
            for pattern in term_patterns:
                matches = re.findall(pattern, content)
                terms.extend(matches)
        
        return terms
    
    def _find_term_variations(self, terms: List[str]) -> Dict[str, List[str]]:
        """Find variations of the same term."""
        variations = {}
        
        # Group similar terms
        for term in terms:
            base = term.lower().strip()
            found = False
            
            for key in variations:
                if self._are_terms_similar(base, key):
                    variations[key].append(term)
                    found = True
                    break
            
            if not found:
                variations[base] = [term]
        
        # Filter out single occurrences
        return {k: list(set(v)) for k, v in variations.items() if len(set(v)) > 1}
    
    def _are_terms_similar(self, term1: str, term2: str) -> bool:
        """Check if two terms are similar (likely variations)."""
        # Simple similarity check
        if term1 == term2:
            return True
        
        # Check for substring relationship
        if term1 in term2 or term2 in term1:
            return True
        
        # Check for common stem
        if len(term1) > 5 and len(term2) > 5:
            if term1[:5] == term2[:5]:
                return True
        
        return False
    
    def _analyze_citation_formats(self, slides: List[Dict[str, Any]]) -> List[str]:
        """Analyze citation formats used in slides."""
        formats = []
        
        citation_patterns = {
            "apa": r'\([A-Z][a-z]+(?:\s+[&,]\s+[A-Z][a-z]+)*,\s+\d{4}\)',  # (Author, 2023)
            "mla": r'[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)*\s+\(\d+\)',  # Author (23)
            "chicago": r'[A-Z][a-z]+,\s+"[^"]+,"',  # Author, "Title,"
            "numbered": r'\[\d+\]',  # [1]
        }
        
        for slide in slides:
            content = self._extract_slide_text(slide)
            for format_name, pattern in citation_patterns.items():
                if re.search(pattern, content):
                    formats.append(format_name)
        
        return list(set(formats))