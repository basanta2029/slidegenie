"""Unit tests for content processor."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from typing import Dict, Any, List

from app.services.ai.content_processor import ContentProcessor
from tests.unit.utils.test_helpers import TestDataGenerator


class TestContentProcessor:
    """Test suite for content processor."""
    
    @pytest.fixture
    def processor(self):
        """Create content processor instance."""
        return ContentProcessor()
    
    @pytest.fixture
    def academic_content(self):
        """Generate sample academic content."""
        return TestDataGenerator.generate_academic_content()
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Mock AI provider for content processing."""
        provider = AsyncMock()
        provider.generate = AsyncMock()
        provider.generate_json = AsyncMock()
        return provider
    
    @pytest.mark.asyncio
    async def test_process_document_sections(self, processor, academic_content):
        """Test processing document into sections."""
        # Process content
        sections = await processor.extract_sections(academic_content)
        
        assert len(sections) > 0
        assert all('heading' in section for section in sections)
        assert all('content' in section for section in sections)
        
        # Verify section order
        expected_order = ["Introduction", "Literature Review", "Methodology", "Results", "Conclusion"]
        actual_order = [section['heading'] for section in sections]
        assert actual_order == expected_order
    
    @pytest.mark.asyncio
    async def test_extract_key_points(self, processor, academic_content, mock_ai_provider):
        """Test key point extraction from content."""
        # Mock AI response
        mock_ai_provider.generate_json.return_value = {
            "key_points": [
                "First major finding from the research",
                "Second important insight discovered",
                "Third critical contribution to the field"
            ],
            "supporting_details": {
                "point_1": ["Evidence A", "Evidence B"],
                "point_2": ["Data analysis results"],
                "point_3": ["Theoretical implications"]
            }
        }
        
        processor.ai_provider = mock_ai_provider
        
        # Extract key points
        key_points = await processor.extract_key_points(
            academic_content['sections'][0]['content']
        )
        
        assert len(key_points['key_points']) == 3
        assert 'supporting_details' in key_points
        mock_ai_provider.generate_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_content(self, processor, academic_content, mock_ai_provider):
        """Test content summarization."""
        # Mock AI response
        mock_ai_provider.generate.return_value = (
            "This research investigates the impact of advanced algorithms on system performance. "
            "Key findings include significant improvements in efficiency and novel applications."
        )
        
        processor.ai_provider = mock_ai_provider
        
        # Summarize content
        summary = await processor.summarize_content(
            academic_content['abstract'],
            max_length=100
        )
        
        assert len(summary) > 0
        assert len(summary.split()) <= 100  # Word count check
        mock_ai_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_citations(self, processor, academic_content):
        """Test citation extraction from content."""
        content_with_citations = """
        Recent studies have shown significant progress (Smith et al., 2023).
        According to Johnson (2022), the methodology is sound.
        Multiple researchers confirm these findings (Brown & Davis, 2021; Wilson, 2023).
        """
        
        citations = await processor.extract_citations(content_with_citations)
        
        assert len(citations) >= 4
        assert any("Smith et al., 2023" in cite for cite in citations)
        assert any("Johnson (2022)" in cite for cite in citations)
        assert any("Brown & Davis, 2021" in cite for cite in citations)
    
    @pytest.mark.asyncio
    async def test_extract_equations(self, processor):
        """Test equation extraction from content."""
        content_with_equations = """
        The fundamental equation is $E = mc^2$ which describes energy-mass equivalence.
        We also use $$\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$ for calculations.
        Inline math like $\\alpha + \\beta = \\gamma$ is also supported.
        """
        
        equations = await processor.extract_equations(content_with_equations)
        
        assert len(equations) == 3
        assert any("E = mc^2" in eq['latex'] for eq in equations)
        assert any("int_{0}" in eq['latex'] for eq in equations)
        assert any(eq['type'] == 'display' for eq in equations)
        assert any(eq['type'] == 'inline' for eq in equations)
    
    @pytest.mark.asyncio
    async def test_extract_figures_and_tables(self, processor):
        """Test figure and table reference extraction."""
        content_with_references = """
        As shown in Figure 1, the results are significant.
        Table 2 presents the detailed comparison.
        See Fig. 3 for the experimental setup.
        The data in Table 4.1 confirms our hypothesis.
        """
        
        figures, tables = await processor.extract_figures_and_tables(content_with_references)
        
        assert len(figures) >= 2
        assert len(tables) >= 2
        assert any("Figure 1" in fig for fig in figures)
        assert any("Table 2" in tab for tab in tables)
    
    @pytest.mark.asyncio
    async def test_chunk_content_for_slides(self, processor, academic_content):
        """Test content chunking for slide creation."""
        # Get a section with multiple paragraphs
        section_content = "\n\n".join(academic_content['sections'][1]['content'])
        
        chunks = await processor.chunk_content_for_slides(
            section_content,
            max_chunk_size=200,  # Characters
            overlap=20
        )
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 220 for chunk in chunks)  # Allow for some overflow
        
        # Check overlap
        for i in range(len(chunks) - 1):
            assert chunks[i][-10:] in chunks[i + 1][:30]  # Some overlap exists
    
    @pytest.mark.asyncio
    async def test_optimize_for_presentation(self, processor, mock_ai_provider):
        """Test content optimization for presentation format."""
        # Mock AI response
        mock_ai_provider.generate_json.return_value = {
            "optimized_content": [
                "• Key insight: Algorithm efficiency improved by 45%",
                "• Novel approach: Hybrid methodology combining ML and traditional methods",
                "• Impact: Reduces computational time from hours to minutes"
            ],
            "visual_suggestions": [
                "Bar chart comparing algorithm performance",
                "Flowchart of the hybrid methodology",
                "Timeline showing computational improvements"
            ],
            "speaker_notes": "Emphasize the practical implications for industry applications"
        }
        
        processor.ai_provider = mock_ai_provider
        
        # Optimize content
        original_content = "Our research demonstrates that the new algorithm..."
        optimized = await processor.optimize_for_presentation(
            original_content,
            slide_type="results"
        )
        
        assert 'optimized_content' in optimized
        assert 'visual_suggestions' in optimized
        assert 'speaker_notes' in optimized
        assert len(optimized['optimized_content']) == 3
    
    @pytest.mark.asyncio
    async def test_extract_acronyms_and_definitions(self, processor):
        """Test acronym and definition extraction."""
        content_with_acronyms = """
        We use Machine Learning (ML) and Artificial Intelligence (AI) techniques.
        The API (Application Programming Interface) provides REST endpoints.
        Natural Language Processing (NLP) is crucial for text analysis.
        """
        
        acronyms = await processor.extract_acronyms(content_with_acronyms)
        
        assert len(acronyms) >= 4
        assert any(acr['acronym'] == 'ML' and acr['definition'] == 'Machine Learning' 
                  for acr in acronyms)
        assert any(acr['acronym'] == 'AI' for acr in acronyms)
        assert any(acr['acronym'] == 'API' for acr in acronyms)
    
    @pytest.mark.asyncio
    async def test_generate_bullet_points(self, processor, mock_ai_provider):
        """Test bullet point generation from paragraph."""
        # Mock AI response
        mock_ai_provider.generate_json.return_value = {
            "bullet_points": [
                "Advanced algorithms reduce processing time by 45%",
                "Novel hybrid approach combines ML with traditional methods",
                "Scalable solution handles datasets up to 1TB",
                "Open-source implementation available on GitHub"
            ]
        }
        
        processor.ai_provider = mock_ai_provider
        
        paragraph = """
        Our research introduces advanced algorithms that significantly reduce processing time,
        achieving up to 45% improvement over existing methods. The novel hybrid approach 
        combines machine learning techniques with traditional algorithmic solutions, creating
        a scalable system capable of handling datasets up to 1TB. We have made the 
        implementation available as open-source on GitHub for community use.
        """
        
        bullets = await processor.generate_bullet_points(
            paragraph,
            max_points=4,
            style="academic"
        )
        
        assert len(bullets['bullet_points']) == 4
        assert all(isinstance(point, str) for point in bullets['bullet_points'])
    
    @pytest.mark.asyncio
    async def test_extract_keywords(self, processor, academic_content, mock_ai_provider):
        """Test keyword extraction for SEO and tagging."""
        # Mock AI response
        mock_ai_provider.generate_json.return_value = {
            "keywords": [
                {"term": "machine learning", "relevance": 0.95},
                {"term": "algorithm optimization", "relevance": 0.88},
                {"term": "computational efficiency", "relevance": 0.82},
                {"term": "hybrid methodology", "relevance": 0.79},
                {"term": "performance analysis", "relevance": 0.75}
            ]
        }
        
        processor.ai_provider = mock_ai_provider
        
        keywords = await processor.extract_keywords(
            academic_content['abstract'],
            max_keywords=5
        )
        
        assert len(keywords['keywords']) == 5
        assert all('term' in kw and 'relevance' in kw for kw in keywords['keywords'])
        assert keywords['keywords'][0]['relevance'] >= keywords['keywords'][-1]['relevance']
    
    @pytest.mark.asyncio
    async def test_validate_academic_content(self, processor):
        """Test academic content validation."""
        # Valid academic content
        valid_content = {
            "title": "A Study on Algorithm Optimization",
            "abstract": "This research presents..." * 20,  # Sufficient length
            "sections": [
                {"heading": "Introduction", "content": ["Text"]},
                {"heading": "Methodology", "content": ["Text"]},
                {"heading": "Results", "content": ["Text"]},
                {"heading": "Conclusion", "content": ["Text"]}
            ],
            "references": ["Ref1", "Ref2", "Ref3"]
        }
        
        is_valid, errors = await processor.validate_academic_content(valid_content)
        assert is_valid
        assert len(errors) == 0
        
        # Invalid content (missing sections)
        invalid_content = {
            "title": "Study",
            "abstract": "Short",
            "sections": [{"heading": "Intro", "content": []}],
            "references": []
        }
        
        is_valid, errors = await processor.validate_academic_content(invalid_content)
        assert not is_valid
        assert len(errors) > 0
        assert any("abstract" in error.lower() for error in errors)
    
    @pytest.mark.asyncio
    async def test_content_difficulty_analysis(self, processor, mock_ai_provider):
        """Test content difficulty and readability analysis."""
        # Mock AI response
        mock_ai_provider.generate_json.return_value = {
            "difficulty_score": 8.5,
            "readability_metrics": {
                "flesch_reading_ease": 35.2,
                "flesch_kincaid_grade": 14.7,
                "gunning_fog": 16.3
            },
            "target_audience": "Graduate students and researchers",
            "complexity_factors": [
                "Technical terminology",
                "Mathematical equations",
                "Complex sentence structures"
            ]
        }
        
        processor.ai_provider = mock_ai_provider
        
        analysis = await processor.analyze_content_difficulty(
            "Complex academic text with equations and technical terms..."
        )
        
        assert 'difficulty_score' in analysis
        assert 'readability_metrics' in analysis
        assert 'target_audience' in analysis
        assert analysis['difficulty_score'] > 7  # High difficulty