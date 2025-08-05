"""Academic content fixtures for testing."""

import pytest
from typing import Dict, List, Any
import json
from pathlib import Path

# Sample research papers
SAMPLE_RESEARCH_PAPERS = {
    "machine_learning": {
        "title": "Deep Learning Approaches for Natural Language Understanding in Academic Contexts",
        "abstract": """This paper presents a comprehensive study of deep learning techniques 
        applied to natural language processing tasks in academic environments. We introduce 
        a novel architecture that combines transformer-based models with domain-specific 
        knowledge graphs to improve understanding of scientific literature. Our approach 
        achieves state-of-the-art results on multiple benchmarks, demonstrating a 15% 
        improvement in comprehension accuracy over existing methods. The implications 
        for automated research assistance and knowledge extraction are discussed.""",
        "keywords": ["deep learning", "NLP", "transformers", "knowledge graphs", "academic AI"],
        "sections": [
            {
                "title": "Introduction",
                "content": "The exponential growth of academic publications...",
            },
            {
                "title": "Related Work",
                "content": "Previous approaches to academic text processing...",
            },
            {
                "title": "Methodology",
                "content": "Our proposed architecture consists of three main components...",
            },
            {
                "title": "Results and Discussion",
                "content": "Experimental evaluation on five benchmark datasets...",
            },
            {
                "title": "Conclusion",
                "content": "This work demonstrates the potential of combining...",
            },
        ],
    },
    "quantum_computing": {
        "title": "Quantum Error Correction in NISQ Devices: A Practical Approach",
        "abstract": """Quantum error correction remains one of the primary challenges in 
        realizing practical quantum computing. This paper presents a novel error correction 
        scheme optimized for Noisy Intermediate-Scale Quantum (NISQ) devices. We demonstrate 
        a 40% reduction in error rates compared to conventional methods while maintaining 
        computational efficiency. Our approach uses topological codes adapted for limited 
        qubit connectivity, making it suitable for current quantum hardware.""",
        "keywords": ["quantum computing", "error correction", "NISQ", "topological codes"],
    },
    "climate_science": {
        "title": "Machine Learning Models for Regional Climate Prediction: A Comparative Study",
        "abstract": """Accurate regional climate prediction is crucial for adaptation planning. 
        This study compares various machine learning approaches for downscaling global climate 
        models to regional scales. We evaluate deep learning, random forests, and gradient 
        boosting methods across multiple climate variables and regions. Our results show that 
        ensemble methods combining multiple ML approaches outperform individual models by 20-30% 
        in prediction accuracy.""",
        "keywords": ["climate modeling", "machine learning", "downscaling", "ensemble methods"],
    },
}

# Conference presentation examples
CONFERENCE_PRESENTATIONS = {
    "icml_2024": {
        "conference": "International Conference on Machine Learning (ICML) 2024",
        "title": "Efficient Transformer Architectures for Long-Context Understanding",
        "duration": 20,
        "sections": [
            "Motivation and Problem Statement",
            "Limitations of Current Approaches",
            "Proposed Architecture",
            "Experimental Setup",
            "Results and Analysis",
            "Future Directions",
        ],
        "key_points": [
            "O(n log n) attention complexity",
            "Maintains full attention expressivity",
            "Scales to 100k+ token sequences",
            "State-of-the-art on long-context benchmarks",
        ],
    },
    "neurips_2024": {
        "conference": "Neural Information Processing Systems (NeurIPS) 2024",
        "title": "Causal Representation Learning in Complex Systems",
        "duration": 15,
        "spotlight": True,
    },
}

# Thesis and dissertation templates
THESIS_TEMPLATES = {
    "phd_computer_science": {
        "degree": "Doctor of Philosophy",
        "field": "Computer Science",
        "chapters": [
            {
                "number": 1,
                "title": "Introduction",
                "sections": [
                    "Background and Motivation",
                    "Problem Statement",
                    "Research Questions",
                    "Contributions",
                    "Thesis Organization",
                ],
            },
            {
                "number": 2,
                "title": "Literature Review",
                "sections": [
                    "Theoretical Foundations",
                    "Related Work in Machine Learning",
                    "Related Work in Applications",
                    "Research Gaps",
                ],
            },
            {
                "number": 3,
                "title": "Theoretical Framework",
                "sections": [
                    "Mathematical Preliminaries",
                    "Problem Formulation",
                    "Proposed Approach",
                    "Theoretical Analysis",
                ],
            },
            {
                "number": 4,
                "title": "Methodology",
                "sections": [
                    "System Architecture",
                    "Algorithm Design",
                    "Implementation Details",
                    "Evaluation Metrics",
                ],
            },
            {
                "number": 5,
                "title": "Experimental Results",
                "sections": [
                    "Experimental Setup",
                    "Baseline Comparisons",
                    "Ablation Studies",
                    "Performance Analysis",
                ],
            },
            {
                "number": 6,
                "title": "Discussion",
                "sections": [
                    "Key Findings",
                    "Implications",
                    "Limitations",
                    "Future Work",
                ],
            },
            {
                "number": 7,
                "title": "Conclusion",
                "sections": [
                    "Summary of Contributions",
                    "Broader Impact",
                    "Final Remarks",
                ],
            },
        ],
    },
    "masters_thesis": {
        "degree": "Master of Science",
        "typical_length": "50-100 pages",
        "chapters": [
            "Introduction",
            "Background and Related Work",
            "Methodology",
            "Implementation",
            "Evaluation",
            "Conclusion and Future Work",
        ],
    },
}

# Citation database samples
CITATION_DATABASE = {
    "apa": [
        "Smith, J. D., & Johnson, K. L. (2023). Advanced machine learning techniques for scientific discovery. Nature Machine Intelligence, 5(3), 234-245.",
        "Brown, M. E., Davis, R. T., & Wilson, S. A. (2022). Quantum computing applications in cryptography. Physical Review Letters, 128(15), 150501.",
        "Garcia, L. M., et al. (2024). Climate change impacts on global food security: A comprehensive review. Science, 380(6642), 456-467.",
    ],
    "ieee": [
        "[1] J. Smith and K. Johnson, \"Advanced machine learning techniques for scientific discovery,\" Nature Mach. Intell., vol. 5, no. 3, pp. 234-245, 2023.",
        "[2] M. Brown, R. Davis, and S. Wilson, \"Quantum computing applications in cryptography,\" Phys. Rev. Lett., vol. 128, no. 15, p. 150501, 2022.",
        "[3] L. Garcia et al., \"Climate change impacts on global food security: A comprehensive review,\" Science, vol. 380, no. 6642, pp. 456-467, 2024.",
    ],
    "bibtex": [
        """@article{smith2023advanced,
  title={Advanced machine learning techniques for scientific discovery},
  author={Smith, John D and Johnson, Karen L},
  journal={Nature Machine Intelligence},
  volume={5},
  number={3},
  pages={234--245},
  year={2023},
  publisher={Nature Publishing Group}
}""",
        """@article{brown2022quantum,
  title={Quantum computing applications in cryptography},
  author={Brown, Michael E and Davis, Robert T and Wilson, Sarah A},
  journal={Physical Review Letters},
  volume={128},
  number={15},
  pages={150501},
  year={2022},
  publisher={American Physical Society}
}""",
    ],
}

# Mathematical formulas and equations
MATHEMATICAL_FORMULAS = {
    "statistics": {
        "mean": r"\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i",
        "variance": r"\sigma^2 = \frac{1}{n-1}\sum_{i=1}^{n} (x_i - \bar{x})^2",
        "standard_deviation": r"\sigma = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n} (x_i - \bar{x})^2}",
        "correlation": r"r = \frac{\sum_{i=1}^{n} (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^{n} (x_i - \bar{x})^2 \sum_{i=1}^{n} (y_i - \bar{y})^2}}",
    },
    "machine_learning": {
        "loss_function": r"\mathcal{L}(\theta) = -\frac{1}{n}\sum_{i=1}^{n} [y_i \log(\hat{y}_i) + (1-y_i)\log(1-\hat{y}_i)]",
        "gradient_descent": r"\theta_{t+1} = \theta_t - \alpha \nabla_\theta \mathcal{L}(\theta_t)",
        "attention": r"\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V",
        "backpropagation": r"\frac{\partial \mathcal{L}}{\partial w_{ij}} = \frac{\partial \mathcal{L}}{\partial a_j} \frac{\partial a_j}{\partial z_j} \frac{\partial z_j}{\partial w_{ij}}",
    },
    "physics": {
        "schrodinger": r"i\hbar\frac{\partial}{\partial t}\Psi = \hat{H}\Psi",
        "einstein": r"E = mc^2",
        "maxwell": r"\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}",
        "thermodynamics": r"dS = \frac{\delta Q_{rev}}{T}",
    },
}

# Scientific diagram descriptions
SCIENTIFIC_DIAGRAMS = {
    "neural_network": {
        "type": "architecture",
        "description": "Multi-layer perceptron with 3 hidden layers",
        "components": [
            "Input layer (784 neurons)",
            "Hidden layer 1 (256 neurons, ReLU)",
            "Hidden layer 2 (128 neurons, ReLU)",
            "Hidden layer 3 (64 neurons, ReLU)",
            "Output layer (10 neurons, Softmax)",
        ],
    },
    "experimental_setup": {
        "type": "flowchart",
        "description": "Data collection and processing pipeline",
        "steps": [
            "Data acquisition from sensors",
            "Preprocessing and filtering",
            "Feature extraction",
            "Model training",
            "Validation and testing",
            "Results analysis",
        ],
    },
    "molecular_structure": {
        "type": "chemical",
        "description": "3D protein structure visualization",
        "elements": ["Alpha helices", "Beta sheets", "Loop regions", "Active site"],
    },
}


@pytest.fixture
def research_paper_content():
    """Fixture providing sample research paper content."""
    return SAMPLE_RESEARCH_PAPERS["machine_learning"]


@pytest.fixture
def conference_presentation():
    """Fixture providing conference presentation example."""
    return CONFERENCE_PRESENTATIONS["icml_2024"]


@pytest.fixture
def phd_thesis_template():
    """Fixture providing PhD thesis template."""
    return THESIS_TEMPLATES["phd_computer_science"]


@pytest.fixture
def citation_samples():
    """Fixture providing citation samples in various formats."""
    return CITATION_DATABASE


@pytest.fixture
def math_formulas():
    """Fixture providing mathematical formulas."""
    return MATHEMATICAL_FORMULAS


@pytest.fixture
def academic_vocabulary():
    """Fixture providing academic vocabulary and phrases."""
    return {
        "transitions": [
            "Furthermore", "Moreover", "In addition", "Consequently",
            "Nevertheless", "However", "In contrast", "Similarly",
            "Therefore", "Thus", "Hence", "Accordingly",
        ],
        "hedging": [
            "may indicate", "suggests that", "appears to be", "could potentially",
            "it is possible that", "tends to", "generally", "typically",
        ],
        "reporting_verbs": [
            "demonstrate", "illustrate", "indicate", "reveal",
            "suggest", "propose", "argue", "maintain",
            "establish", "confirm", "validate", "corroborate",
        ],
        "academic_phrases": [
            "The purpose of this study is to",
            "This paper aims to investigate",
            "The results indicate that",
            "Our findings suggest that",
            "Further research is needed to",
            "The implications of these findings are",
            "This study contributes to the literature by",
            "The limitations of this study include",
        ],
    }


@pytest.fixture
def sample_abstract():
    """Fixture providing a well-structured academic abstract."""
    return {
        "background": "The increasing complexity of modern software systems demands more sophisticated testing approaches.",
        "objective": "This study investigates the effectiveness of AI-powered test generation techniques in improving code coverage and bug detection.",
        "methods": "We conducted a comparative analysis of traditional and AI-based testing methods across 50 open-source projects, measuring coverage metrics and defect discovery rates.",
        "results": "AI-powered approaches achieved 35% higher code coverage and detected 2.3x more edge-case bugs compared to conventional methods.",
        "conclusion": "The integration of AI in software testing significantly enhances quality assurance processes, though challenges remain in handling domain-specific constraints.",
        "full_text": """The increasing complexity of modern software systems demands more sophisticated testing approaches. This study investigates the effectiveness of AI-powered test generation techniques in improving code coverage and bug detection. We conducted a comparative analysis of traditional and AI-based testing methods across 50 open-source projects, measuring coverage metrics and defect discovery rates. AI-powered approaches achieved 35% higher code coverage and detected 2.3x more edge-case bugs compared to conventional methods. The integration of AI in software testing significantly enhances quality assurance processes, though challenges remain in handling domain-specific constraints.""",
    }


@pytest.fixture
def presentation_outline():
    """Fixture providing a complete presentation outline."""
    return {
        "title": "Advances in Quantum Machine Learning",
        "duration": 20,
        "slides": [
            {
                "number": 1,
                "type": "title",
                "duration": 30,
                "content": {
                    "title": "Advances in Quantum Machine Learning",
                    "subtitle": "Bridging Quantum Computing and AI",
                    "authors": ["Dr. Jane Smith", "Prof. John Doe"],
                    "affiliation": "Quantum AI Research Lab, MIT",
                },
            },
            {
                "number": 2,
                "type": "outline",
                "duration": 45,
                "content": {
                    "title": "Outline",
                    "sections": [
                        "Introduction to Quantum ML",
                        "Quantum Advantage in ML Tasks",
                        "Current Algorithms and Applications",
                        "Experimental Results",
                        "Challenges and Future Directions",
                    ],
                },
            },
            {
                "number": 3,
                "type": "content",
                "duration": 90,
                "content": {
                    "title": "Why Quantum Machine Learning?",
                    "bullets": [
                        "Exponential speedup for certain problems",
                        "Enhanced feature spaces through quantum entanglement",
                        "Natural representation of quantum systems",
                        "Potential for solving intractable classical problems",
                    ],
                },
            },
            # Additional slides...
        ],
    }


@pytest.fixture
def load_academic_fixtures():
    """Load all academic fixture files from the fixtures directory."""
    fixtures_dir = Path(__file__).parent / "files" / "academic"
    fixtures = {}
    
    if fixtures_dir.exists():
        for file_path in fixtures_dir.glob("*.json"):
            with open(file_path, "r") as f:
                fixtures[file_path.stem] = json.load(f)
    
    return fixtures