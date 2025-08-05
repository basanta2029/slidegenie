"""Unit tests for academic analyzer."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from typing import Dict, Any, List

from app.services.document_processing.analyzers.academic_analyzer import AcademicAnalyzer
from tests.unit.utils.test_helpers import TestDataGenerator


class TestAcademicAnalyzer:
    """Test suite for academic document analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create academic analyzer instance."""
        return AcademicAnalyzer()
    
    @pytest.fixture
    def academic_content(self):
        """Generate sample academic content."""
        return TestDataGenerator.generate_academic_content()
    
    @pytest.fixture
    def research_paper_content(self):
        """Generate realistic research paper content."""
        return {
            "title": "Deep Learning Approaches for Natural Language Understanding: A Comprehensive Survey",
            "authors": [
                {"name": "John Doe", "affiliation": "MIT"},
                {"name": "Jane Smith", "affiliation": "Stanford"}
            ],
            "abstract": """
            This paper presents a comprehensive survey of deep learning approaches for natural language 
            understanding (NLU). We systematically review recent advances in neural architectures, 
            including transformers, BERT, and GPT models. Our analysis covers 150+ papers published 
            between 2018-2024, identifying key trends and future directions. We provide a taxonomy of 
            NLU tasks and evaluate state-of-the-art models across multiple benchmarks. Our findings 
            suggest that while significant progress has been made, challenges remain in areas such as 
            common-sense reasoning and cross-lingual transfer.
            """,
            "sections": [
                {
                    "title": "Introduction",
                    "content": """Natural language understanding has seen remarkable progress with the advent 
                    of deep learning. This survey aims to provide researchers with a comprehensive overview 
                    of current approaches and future challenges.""",
                    "citations": ["(Vaswani et al., 2017)", "(Devlin et al., 2018)", "(Brown et al., 2020)"]
                },
                {
                    "title": "Related Work",
                    "content": """Previous surveys have focused on specific aspects of NLU. Smith et al. (2019) 
                    reviewed traditional methods, while Johnson (2020) focused on transformer architectures.""",
                    "citations": ["(Smith et al., 2019)", "(Johnson, 2020)"]
                },
                {
                    "title": "Methodology",
                    "content": """We conducted a systematic literature review following PRISMA guidelines. 
                    Papers were selected based on impact factor, citation count, and relevance.""",
                    "subsections": [
                        {"title": "Search Strategy", "content": "We searched major databases..."},
                        {"title": "Inclusion Criteria", "content": "Papers were included if..."}
                    ]
                },
                {
                    "title": "Results",
                    "content": """Our analysis identified three main categories of approaches: 
                    1) Attention-based models, 2) Pre-trained language models, 3) Multi-modal architectures.""",
                    "figures": ["Figure 1: Taxonomy of NLU approaches", "Figure 2: Performance comparison"],
                    "tables": ["Table 1: Benchmark results", "Table 2: Model characteristics"]
                },
                {
                    "title": "Discussion",
                    "content": """The results demonstrate significant improvements in NLU tasks. However, 
                    several limitations persist, particularly in handling ambiguity and context."""
                },
                {
                    "title": "Conclusion",
                    "content": """This survey provides a comprehensive overview of deep learning for NLU. 
                    Future work should focus on interpretability and efficiency."""
                }
            ],
            "references": [
                "Vaswani, A., et al. (2017). Attention is all you need. NeurIPS.",
                "Devlin, J., et al. (2018). BERT: Pre-training of deep bidirectional transformers. NAACL.",
                "Brown, T., et al. (2020). Language models are few-shot learners. NeurIPS."
            ]
        }
    
    @pytest.mark.asyncio
    async def test_analyze_document_type(self, analyzer, academic_content):
        """Test document type identification."""
        # Research paper
        paper_type = await analyzer.identify_document_type(academic_content)
        assert paper_type == "research_paper"
        
        # Thesis/Dissertation
        thesis_content = academic_content.copy()
        thesis_content['chapters'] = thesis_content.pop('sections')
        thesis_content['acknowledgments'] = "I would like to thank..."
        thesis_type = await analyzer.identify_document_type(thesis_content)
        assert thesis_type == "thesis"
        
        # Review article
        review_content = academic_content.copy()
        review_content['title'] = "A Systematic Review of Machine Learning in Healthcare"
        review_type = await analyzer.identify_document_type(review_content)
        assert review_type == "review"
    
    @pytest.mark.asyncio
    async def test_extract_research_components(self, analyzer, research_paper_content):
        """Test extraction of key research components."""
        components = await analyzer.extract_research_components(research_paper_content)
        
        assert 'research_question' in components
        assert 'hypothesis' in components
        assert 'methodology' in components
        assert 'findings' in components
        assert 'contributions' in components
        assert 'limitations' in components
        assert 'future_work' in components
        
        # Verify methodology extraction
        assert components['methodology'] is not None
        assert 'systematic literature review' in components['methodology'].lower()
        assert 'PRISMA' in components['methodology']
    
    @pytest.mark.asyncio
    async def test_analyze_citation_network(self, analyzer, research_paper_content):
        """Test citation network analysis."""
        citation_analysis = await analyzer.analyze_citations(research_paper_content)
        
        assert 'total_citations' in citation_analysis
        assert 'unique_authors' in citation_analysis
        assert 'citation_years' in citation_analysis
        assert 'most_cited_authors' in citation_analysis
        assert 'citation_patterns' in citation_analysis
        
        # Verify citation count
        assert citation_analysis['total_citations'] >= 5
        assert 'Vaswani' in citation_analysis['unique_authors']
        assert 2017 in citation_analysis['citation_years']
    
    @pytest.mark.asyncio
    async def test_identify_research_methods(self, analyzer, research_paper_content):
        """Test research methodology identification."""
        methods = await analyzer.identify_research_methods(research_paper_content)
        
        assert 'approach' in methods
        assert 'data_collection' in methods
        assert 'analysis_techniques' in methods
        assert 'validation_methods' in methods
        
        # Verify specific methods
        assert methods['approach'] == 'systematic_review'
        assert 'literature_review' in methods['data_collection']
    
    @pytest.mark.asyncio
    async def test_extract_key_findings(self, analyzer, research_paper_content):
        """Test key findings extraction."""
        findings = await analyzer.extract_key_findings(research_paper_content)
        
        assert isinstance(findings, list)
        assert len(findings) > 0
        
        # Verify finding structure
        for finding in findings:
            assert 'statement' in finding
            assert 'evidence' in finding
            assert 'significance' in finding
            assert 'confidence' in finding
    
    @pytest.mark.asyncio
    async def test_assess_academic_quality(self, analyzer, research_paper_content):
        """Test academic quality assessment."""
        quality_metrics = await analyzer.assess_quality(research_paper_content)
        
        assert 'overall_score' in quality_metrics
        assert 'criteria_scores' in quality_metrics
        assert 'strengths' in quality_metrics
        assert 'weaknesses' in quality_metrics
        assert 'recommendations' in quality_metrics
        
        # Check specific criteria
        criteria = quality_metrics['criteria_scores']
        assert 'clarity' in criteria
        assert 'methodology_rigor' in criteria
        assert 'literature_coverage' in criteria
        assert 'contribution_significance' in criteria
        assert 'presentation_quality' in criteria
        
        # Verify score ranges
        assert 0 <= quality_metrics['overall_score'] <= 100
        assert all(0 <= score <= 100 for score in criteria.values())
    
    @pytest.mark.asyncio
    async def test_extract_theoretical_framework(self, analyzer, research_paper_content):
        """Test theoretical framework extraction."""
        framework = await analyzer.extract_theoretical_framework(research_paper_content)
        
        assert 'theories' in framework
        assert 'concepts' in framework
        assert 'relationships' in framework
        assert 'assumptions' in framework
        
        # Verify framework elements
        assert len(framework['concepts']) > 0
        assert any('deep learning' in concept.lower() for concept in framework['concepts'])
    
    @pytest.mark.asyncio
    async def test_analyze_argument_structure(self, analyzer, research_paper_content):
        """Test argument structure analysis."""
        argument = await analyzer.analyze_argument_structure(research_paper_content)
        
        assert 'main_claim' in argument
        assert 'supporting_claims' in argument
        assert 'evidence' in argument
        assert 'counter_arguments' in argument
        assert 'logical_flow' in argument
        
        # Verify logical flow
        assert argument['logical_flow']['coherence_score'] > 0.7
        assert 'transitions' in argument['logical_flow']
    
    @pytest.mark.asyncio
    async def test_extract_statistical_analyses(self, analyzer):
        """Test statistical analysis extraction."""
        content_with_stats = {
            "results": """
            Our analysis showed significant improvements (p < 0.001, n=1000).
            The mean accuracy was 92.5% (SD = 3.2), compared to baseline 85.3% (SD = 4.1).
            Cohen's d = 1.92 indicated a large effect size.
            Regression analysis revealed R² = 0.87, F(3,96) = 45.2, p < 0.001.
            """
        }
        
        stats = await analyzer.extract_statistical_analyses(content_with_stats)
        
        assert 'significance_tests' in stats
        assert 'descriptive_stats' in stats
        assert 'effect_sizes' in stats
        assert 'regression_results' in stats
        
        # Verify specific statistics
        assert any(test['p_value'] < 0.001 for test in stats['significance_tests'])
        assert any(stat['mean'] == 92.5 for stat in stats['descriptive_stats'])
        assert any(effect['cohen_d'] == 1.92 for effect in stats['effect_sizes'])
    
    @pytest.mark.asyncio
    async def test_identify_research_gaps(self, analyzer, research_paper_content):
        """Test research gap identification."""
        gaps = await analyzer.identify_research_gaps(research_paper_content)
        
        assert isinstance(gaps, list)
        assert len(gaps) > 0
        
        for gap in gaps:
            assert 'description' in gap
            assert 'importance' in gap
            assert 'suggested_approach' in gap
            assert 'related_work' in gap
    
    @pytest.mark.asyncio
    async def test_extract_contributions(self, analyzer, research_paper_content):
        """Test contribution extraction."""
        contributions = await analyzer.extract_contributions(research_paper_content)
        
        assert 'theoretical' in contributions
        assert 'methodological' in contributions
        assert 'empirical' in contributions
        assert 'practical' in contributions
        
        # Verify at least one type of contribution exists
        assert any(len(contrib_list) > 0 for contrib_list in contributions.values())
    
    @pytest.mark.asyncio
    async def test_analyze_literature_review(self, analyzer, research_paper_content):
        """Test literature review analysis."""
        lit_analysis = await analyzer.analyze_literature_review(research_paper_content)
        
        assert 'coverage' in lit_analysis
        assert 'recency' in lit_analysis
        assert 'diversity' in lit_analysis
        assert 'critical_analysis' in lit_analysis
        assert 'synthesis_quality' in lit_analysis
        assert 'gaps_identified' in lit_analysis
        
        # Verify metrics
        assert 0 <= lit_analysis['coverage']['score'] <= 1
        assert 'recent_papers_ratio' in lit_analysis['recency']
    
    @pytest.mark.asyncio
    async def test_extract_keywords_and_topics(self, analyzer, research_paper_content):
        """Test keyword and topic extraction."""
        analysis = await analyzer.extract_keywords_and_topics(research_paper_content)
        
        assert 'keywords' in analysis
        assert 'topics' in analysis
        assert 'topic_distribution' in analysis
        assert 'keyword_relevance' in analysis
        
        # Verify keywords
        keywords = analysis['keywords']
        assert any('deep learning' in kw.lower() for kw in keywords)
        assert any('natural language' in kw.lower() for kw in keywords)
        
        # Verify topics
        assert len(analysis['topics']) > 0
        assert all('name' in topic and 'weight' in topic for topic in analysis['topics'])
    
    @pytest.mark.asyncio
    async def test_generate_presentation_outline(self, analyzer, research_paper_content):
        """Test presentation outline generation from academic content."""
        outline = await analyzer.generate_presentation_outline(
            research_paper_content,
            duration_minutes=20,
            audience="academic_conference"
        )
        
        assert 'slides' in outline
        assert 'total_slides' in outline
        assert 'time_allocation' in outline
        assert 'key_visuals' in outline
        
        # Verify slide structure
        slides = outline['slides']
        assert slides[0]['type'] == 'title'
        assert any(slide['type'] == 'introduction' for slide in slides)
        assert any(slide['type'] == 'methodology' for slide in slides)
        assert any(slide['type'] == 'results' for slide in slides)
        assert any(slide['type'] == 'conclusion' for slide in slides)
        
        # Verify time allocation
        total_time = sum(slide.get('duration', 0) for slide in slides)
        assert 18 <= total_time <= 22  # Within reasonable range of 20 minutes