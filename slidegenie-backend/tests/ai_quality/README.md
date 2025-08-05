# AI Quality Testing Framework for SlideGenie

A comprehensive suite for testing and validating AI-generated academic content quality, ensuring high standards for presentations, citations, and specialized content.

## Overview

The AI Quality Testing Framework provides:

- **Prompt Effectiveness Testing**: Measure and optimize prompt strategies
- **Output Quality Validation**: Ensure coherence, grammar, and academic tone
- **Academic Accuracy Testing**: Verify facts, citations, and references
- **Specialized Content Verification**: Validate equations, code, formulas, and tables
- **Benchmark Evaluation**: Compare against known quality standards
- **Human-in-the-Loop Validation**: Integrate human expertise for quality assurance

## Components

### 1. Prompt Effectiveness (`prompt_effectiveness.py`)

Tests the effectiveness of prompts used for AI content generation.

**Features:**
- Response relevance scoring
- Token efficiency calculation
- Prompt injection resistance testing
- Context window optimization
- Multi-strategy comparison

**Example Usage:**
```python
from tests.ai_quality import PromptEffectivenessTest

test = PromptEffectivenessTest()
result = test.evaluate({
    "prompt": "Generate introduction slides for machine learning paper",
    "context": {"paper_title": "Deep Learning in Healthcare"}
})

print(f"Relevance Score: {result.relevance_score}")
print(f"Token Efficiency: {result.token_efficiency}")
print(f"Injection Resistant: {result.injection_resistance}")
```

### 2. Output Quality Validation (`output_quality.py`)

Validates the quality of AI-generated slide content.

**Features:**
- Coherence and logical flow assessment
- Grammar and spelling checking
- Academic tone verification
- Visual balance evaluation
- Consistency checking across slides
- Readability analysis

**Example Usage:**
```python
from tests.ai_quality import OutputQualityValidator

validator = OutputQualityValidator()
metrics = validator.validate({
    "slides": [
        {
            "title": "Introduction",
            "content": "Deep learning has revolutionized AI...",
            "bullet_points": ["Point 1", "Point 2", "Point 3"]
        }
    ]
})

print(f"Coherence Score: {metrics.coherence_score}")
print(f"Academic Tone Score: {metrics.academic_tone_score}")
print(f"Issues Found: {len(metrics.issues)}")
```

### 3. Academic Accuracy Testing (`academic_accuracy.py`)

Tests academic accuracy including fact checking and citation verification.

**Features:**
- Fact verification against academic standards
- Citation accuracy and completeness checking
- Reference format validation
- Terminology consistency analysis
- Statistical claim validation

**Example Usage:**
```python
from tests.ai_quality import AcademicAccuracyTest

test = AcademicAccuracyTest()
result = test.assess({
    "slides": slides_data,
    "references": citations_list
})

print(f"Fact Accuracy: {result.fact_accuracy_score}")
print(f"Citation Accuracy: {result.citation_accuracy_score}")
print(f"Verified Facts: {len(result.verified_facts)}")
```

### 4. Specialized Content Testing (`specialized_content.py`)

Verifies specialized academic content types.

**Features:**
- Mathematical equation validation (LaTeX, Unicode, ASCII)
- Code snippet syntax checking
- Chemical formula verification
- Diagram description quality assessment
- Table structure and data integrity validation

**Example Usage:**
```python
from tests.ai_quality import SpecializedContentTest

test = SpecializedContentTest()
result = test.verify({
    "slides": [
        {
            "content": "The equation $E = mc^2$ shows...",
            "has_equation": True
        }
    ]
})

print(f"Equation Accuracy: {result.equation_accuracy}")
print(f"Verified Content: {len(result.verified_content)}")
```

### 5. Quality Scoring (`scoring.py`)

Provides comprehensive scoring algorithms for overall quality assessment.

**Features:**
- Weighted multi-dimensional scoring
- Letter grade assignment (A+ to F)
- Percentile ranking
- Strength and weakness identification
- Actionable recommendation generation

**Example Usage:**
```python
from tests.ai_quality import QualityScorer

scorer = QualityScorer()
quality_score = scorer.calculate_overall_score(all_test_results)

print(f"Overall Score: {quality_score.weighted_score:.2%}")
print(f"Grade: {quality_score.grade}")
print(f"Percentile: {quality_score.percentile:.1f}%")

# Generate detailed report
report = scorer.generate_detailed_report(quality_score, all_test_results)
```

### 6. Validators (`validators.py`)

Provides specialized validators for references and content.

**Features:**
- Reference format validation (APA, MLA, Chicago, IEEE)
- DOI and URL validation
- Citation consistency checking
- Content integrity verification
- Statistical claim validation

**Example Usage:**
```python
from tests.ai_quality import ReferenceValidator, ContentValidator

# Validate references
ref_validator = ReferenceValidator()
ref_result = ref_validator.validate_reference(citation)

# Validate content
content_validator = ContentValidator()
content_result = content_validator.validate_content(text, references)
```

### 7. Benchmarks (`benchmarks.py`)

Manages benchmark datasets and evaluation metrics.

**Features:**
- Pre-defined benchmark cases for different content types
- Performance metric calculation
- Human-AI agreement assessment
- Trend analysis over time

**Example Usage:**
```python
from tests.ai_quality import BenchmarkDataset, EvaluationMetrics

dataset = BenchmarkDataset()
metrics = EvaluationMetrics()

# Get benchmark cases
cases = dataset.get_dataset("academic_writing")

# Evaluate against benchmark
result = metrics.evaluate_benchmark(
    benchmark_case,
    actual_output,
    actual_scores,
    execution_time_ms
)
```

### 8. Human Validation (`human_validation.py`)

Implements human-in-the-loop validation tools.

**Features:**
- Task creation for human validators
- Quality rating interfaces
- A/B comparison tools
- Error detection workflows
- Inter-rater reliability calculation
- Consensus analysis

**Example Usage:**
```python
from tests.ai_quality.human_validation import HumanValidationInterface

interface = HumanValidationInterface()

# Create validation task
task = interface.create_quality_rating_task(
    content=slide_content,
    dimensions=["coherence", "accuracy", "clarity"]
)

# Start validation session
session = interface.start_validation_session("validator_123")

# Get and complete tasks
next_task = interface.get_next_task(session.id)
interface.submit_task_response(
    task_id=next_task.id,
    response={"ratings": {"coherence": 4, "accuracy": 5}},
    confidence=0.9,
    time_spent_seconds=60
)
```

## Running the Full Quality Suite

To run a comprehensive quality assessment:

```python
from tests.ai_quality import run_full_quality_suite

# Prepare your content
content = {
    "slides": [...],
    "references": [...],
    "prompt": "...",
    "context": {...}
}

# Run full suite
results = run_full_quality_suite(content)

# Access results
print(f"Overall Score: {results['overall_score'].weighted_score:.2%}")
print(f"Grade: {results['overall_score'].grade}")
```

## Configuration

### Quality Thresholds

Adjust quality thresholds in `scoring.py`:

```python
self.grade_thresholds = {
    "A+": 0.95,
    "A": 0.90,
    "B+": 0.80,
    # ...
}
```

### Dimension Weights

Customize dimension weights for your use case:

```python
self.dimension_weights = {
    "prompt_effectiveness": {
        "relevance": 0.25,
        "efficiency": 0.20,
        # ...
    }
}
```

## Testing

Run the test suite:

```bash
# Run all AI quality tests
pytest tests/ai_quality/test_ai_quality_suite.py -v

# Run specific test
pytest tests/ai_quality/test_ai_quality_suite.py::TestAIQualitySuite::test_output_quality_validation -v
```

## Best Practices

1. **Regular Benchmarking**: Run benchmark evaluations regularly to track quality trends
2. **Human Validation**: Integrate human validation for critical content
3. **Custom Validators**: Extend validators for domain-specific requirements
4. **Continuous Monitoring**: Track quality metrics over time
5. **Feedback Loop**: Use quality scores to improve prompts and models

## Integration with SlideGenie

The AI Quality Testing Framework integrates seamlessly with SlideGenie's content generation pipeline:

```python
# In your generation service
from tests.ai_quality import run_full_quality_suite

async def generate_presentation(request):
    # Generate content
    content = await ai_service.generate(request)
    
    # Run quality checks
    quality_results = run_full_quality_suite(content)
    
    # Only proceed if quality meets threshold
    if quality_results['overall_score'].weighted_score >= 0.80:
        return content
    else:
        # Regenerate or apply improvements
        return await improve_content(content, quality_results)
```

## Extending the Framework

To add custom quality checks:

1. Create a new test class following the existing pattern
2. Implement the assessment method
3. Add to the quality scorer
4. Update the `run_full_quality_suite` function

Example:
```python
class CustomDomainTest:
    def assess(self, content: Dict[str, Any]) -> CustomResult:
        # Implement domain-specific checks
        pass
```

## Performance Considerations

- **Caching**: Cache validation results for repeated content
- **Parallel Processing**: Run independent tests in parallel
- **Selective Testing**: Run only necessary tests based on content type
- **Batch Processing**: Process multiple presentations together

## Contributing

When adding new quality tests:
1. Follow the existing structure and naming conventions
2. Include comprehensive docstrings
3. Add unit tests
4. Update this README
5. Consider performance impact

## License

This AI Quality Testing Framework is part of the SlideGenie project and follows the same license terms.