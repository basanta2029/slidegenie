"""Academic content factories for testing."""

import factory
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import random
import json

from .base import BaseFactory, DictFactory, academic_fake, fake


class CitationFactory(DictFactory):
    """Factory for creating citation test data."""
    
    id = factory.Sequence(lambda n: f"citation_{n}")
    
    # Basic citation info
    authors = factory.LazyAttribute(
        lambda o: [
            {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "middle_initial": fake.random_letter().upper() if random.random() > 0.5 else None,
                "orcid": f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-"
                         f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
                         if random.random() > 0.7 else None,
            }
            for _ in range(random.randint(1, 6))
        ]
    )
    
    year = factory.LazyAttribute(lambda o: random.randint(1990, 2024))
    title = factory.LazyAttribute(lambda o: academic_fake.research_title())
    
    # Publication details
    publication_type = factory.LazyAttribute(
        lambda o: random.choice([
            "journal_article", "conference_paper", "book",
            "book_chapter", "thesis", "technical_report", "preprint"
        ])
    )
    
    journal = factory.LazyAttribute(
        lambda o: BaseFactory.random_journal() 
        if o.publication_type == "journal_article" else None
    )
    
    conference = factory.LazyAttribute(
        lambda o: BaseFactory.random_conference() 
        if o.publication_type == "conference_paper" else None
    )
    
    book_title = factory.LazyAttribute(
        lambda o: fake.sentence(nb_words=6)[:-1] 
        if o.publication_type in ["book", "book_chapter"] else None
    )
    
    publisher = factory.LazyAttribute(
        lambda o: random.choice([
            "Springer", "Elsevier", "IEEE", "ACM", "Nature Publishing Group",
            "Oxford University Press", "Cambridge University Press", "Wiley"
        ]) if o.publication_type in ["book", "book_chapter"] else None
    )
    
    # Volume, issue, pages
    volume = factory.LazyAttribute(
        lambda o: str(random.randint(1, 200)) 
        if o.publication_type == "journal_article" else None
    )
    
    issue = factory.LazyAttribute(
        lambda o: str(random.randint(1, 12)) 
        if o.publication_type == "journal_article" and random.random() > 0.3 else None
    )
    
    pages = factory.LazyAttribute(lambda o: {
        "journal_article": f"{random.randint(1, 500)}-{random.randint(501, 600)}",
        "conference_paper": f"{random.randint(1, 10)}-{random.randint(11, 20)}",
        "book_chapter": f"{random.randint(1, 50)}-{random.randint(51, 100)}",
    }.get(o.publication_type))
    
    # Digital identifiers
    doi = factory.LazyAttribute(
        lambda o: f"10.{random.randint(1000, 9999)}/{BaseFactory.random_string(10)}"
        if random.random() > 0.2 else None
    )
    
    arxiv_id = factory.LazyAttribute(
        lambda o: f"{random.randint(2015, 2024)}.{random.randint(10000, 99999)}"
        if o.publication_type == "preprint" else None
    )
    
    pmid = factory.LazyAttribute(
        lambda o: str(random.randint(10000000, 99999999))
        if o.journal and random.random() > 0.7 else None
    )
    
    # Citation metrics
    citation_count = factory.LazyAttribute(
        lambda o: int(random.lognormvariate(2, 1.5) * (2024 - o.year))
    )
    
    # Abstract and keywords
    abstract = factory.LazyAttribute(lambda o: academic_fake.abstract())
    keywords = factory.LazyAttribute(lambda o: BaseFactory.random_research_keywords())
    
    # URLs
    url = factory.LazyAttribute(
        lambda o: f"https://doi.org/{o.doi}" if o.doi else fake.url()
    )
    
    pdf_url = factory.LazyAttribute(
        lambda o: f"https://arxiv.org/pdf/{o.arxiv_id}.pdf" 
        if o.arxiv_id else None
    )
    
    # Citation styles
    formatted_citations = factory.LazyAttribute(lambda o: {
        "apa": _format_citation_apa(o),
        "mla": _format_citation_mla(o),
        "chicago": _format_citation_chicago(o),
        "ieee": _format_citation_ieee(o),
        "bibtex": _format_citation_bibtex(o),
    })
    
    class Params:
        recent = factory.Trait(
            year=factory.LazyAttribute(lambda o: random.randint(2020, 2024)),
            citation_count=factory.LazyAttribute(lambda o: random.randint(0, 50)),
        )
        
        highly_cited = factory.Trait(
            citation_count=factory.LazyAttribute(lambda o: random.randint(100, 5000)),
            journal=factory.LazyAttribute(
                lambda o: random.choice(["Nature", "Science", "Cell"])
            ),
        )


class ResearchPaperFactory(DictFactory):
    """Factory for research paper content."""
    
    id = factory.Sequence(lambda n: f"paper_{n}")
    
    # Basic metadata
    title = factory.LazyAttribute(lambda o: academic_fake.research_title())
    authors = factory.LazyAttribute(
        lambda o: [
            {
                "name": fake.name(),
                "affiliation": BaseFactory.random_university(),
                "email": BaseFactory.random_email(),
                "corresponding": i == 0,
            }
            for i in range(random.randint(1, 6))
        ]
    )
    
    # Paper content
    abstract = factory.LazyAttribute(lambda o: academic_fake.abstract(8))
    
    sections = factory.LazyAttribute(lambda o: [
        {
            "title": "Introduction",
            "content": fake.text(max_nb_chars=2000),
            "subsections": [],
        },
        {
            "title": "Related Work",
            "content": fake.text(max_nb_chars=1500),
            "subsections": [
                {
                    "title": fake.sentence(nb_words=4)[:-1],
                    "content": fake.text(max_nb_chars=800),
                }
                for _ in range(random.randint(2, 4))
            ],
        },
        {
            "title": "Methodology",
            "content": fake.text(max_nb_chars=2500),
            "subsections": [
                {
                    "title": random.choice([
                        "Data Collection", "Experimental Setup",
                        "Model Architecture", "Algorithm Design"
                    ]),
                    "content": fake.text(max_nb_chars=1000),
                }
                for _ in range(random.randint(2, 5))
            ],
        },
        {
            "title": "Results",
            "content": fake.text(max_nb_chars=2000),
            "subsections": [
                {
                    "title": f"Experiment {i+1}",
                    "content": fake.text(max_nb_chars=600),
                }
                for i in range(random.randint(2, 4))
            ],
        },
        {
            "title": "Discussion",
            "content": fake.text(max_nb_chars=1800),
            "subsections": [],
        },
        {
            "title": "Conclusion",
            "content": fake.text(max_nb_chars=1000),
            "subsections": [],
        },
    ])
    
    # Academic elements
    keywords = factory.LazyAttribute(lambda o: BaseFactory.random_research_keywords())
    
    equations = factory.LazyAttribute(
        lambda o: [
            {
                "label": f"eq:{i+1}",
                "latex": academic_fake.equation(),
                "description": fake.sentence(),
            }
            for i in range(random.randint(5, 15))
        ]
    )
    
    figures = factory.LazyAttribute(
        lambda o: [
            {
                "id": f"fig:{i+1}",
                "caption": fake.text(max_nb_chars=200),
                "url": f"https://placeholder.com/{random.randint(600, 800)}x{random.randint(400, 600)}",
                "type": random.choice(["graph", "diagram", "photo", "chart"]),
            }
            for i in range(random.randint(3, 10))
        ]
    )
    
    tables = factory.LazyAttribute(
        lambda o: [
            {
                "id": f"table:{i+1}",
                "caption": fake.sentence(),
                "headers": [fake.word() for _ in range(random.randint(3, 6))],
                "rows": [
                    [str(random.uniform(0, 100))[:5] for _ in range(len(o.tables[i]["headers"]))]
                    for _ in range(random.randint(5, 15))
                ] if i < len(o.tables) else [],
            }
            for i in range(random.randint(1, 5))
        ]
    )
    
    references = factory.LazyAttribute(
        lambda o: [CitationFactory() for _ in range(random.randint(20, 50))]
    )
    
    # Metadata
    submitted_date = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(180))
    accepted_date = factory.LazyAttribute(
        lambda o: o.submitted_date + timedelta(days=random.randint(30, 180))
        if random.random() > 0.3 else None
    )
    published_date = factory.LazyAttribute(
        lambda o: o.accepted_date + timedelta(days=random.randint(7, 30))
        if o.accepted_date else None
    )
    
    # Venue information
    venue_type = factory.LazyAttribute(
        lambda o: random.choice(["journal", "conference", "workshop", "arxiv"])
    )
    venue_name = factory.LazyAttribute(
        lambda o: BaseFactory.random_journal() if o.venue_type == "journal"
        else BaseFactory.random_conference() if o.venue_type == "conference"
        else "arXiv" if o.venue_type == "arxiv"
        else fake.company() + " Workshop"
    )
    
    # Review information
    peer_reviewed = factory.LazyAttribute(lambda o: o.venue_type != "arxiv")
    review_score = factory.LazyAttribute(
        lambda o: random.uniform(0.5, 1.0) if o.peer_reviewed else None
    )


class ThesisFactory(DictFactory):
    """Factory for thesis/dissertation content."""
    
    id = factory.Sequence(lambda n: f"thesis_{n}")
    
    # Basic info
    title = factory.LazyAttribute(lambda o: academic_fake.research_title())
    author = factory.LazyAttribute(lambda o: {
        "name": fake.name(),
        "email": BaseFactory.random_email(),
        "student_id": BaseFactory.random_string(8, "S"),
    })
    
    # Thesis metadata
    thesis_type = factory.LazyAttribute(
        lambda o: random.choice(["phd", "masters", "undergraduate"])
    )
    
    degree = factory.LazyAttribute(lambda o: {
        "phd": "Doctor of Philosophy",
        "masters": random.choice(["Master of Science", "Master of Arts"]),
        "undergraduate": random.choice(["Bachelor of Science", "Bachelor of Arts"]),
    }[o.thesis_type])
    
    department = factory.LazyAttribute(lambda o: BaseFactory.random_department())
    university = factory.LazyAttribute(lambda o: BaseFactory.random_university())
    
    # Committee
    committee = factory.LazyAttribute(lambda o: [
        {
            "name": fake.name(),
            "title": BaseFactory.random_academic_title(),
            "role": "Advisor" if i == 0 else 
                   "Co-advisor" if i == 1 and random.random() > 0.7 else 
                   "Committee Member",
            "department": BaseFactory.random_department(),
        }
        for i in range(random.randint(3, 6))
    ])
    
    # Thesis content (extended)
    abstract = factory.LazyAttribute(lambda o: academic_fake.abstract(12))
    acknowledgments = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=1000))
    
    chapters = factory.LazyAttribute(lambda o: _generate_thesis_chapters(o.thesis_type))
    
    # Appendices
    appendices = factory.LazyAttribute(
        lambda o: [
            {
                "title": f"Appendix {chr(65 + i)}: {fake.sentence(nb_words=4)[:-1]}",
                "content": fake.text(max_nb_chars=1500),
            }
            for i in range(random.randint(0, 3))
        ]
    )
    
    # Metadata
    submission_date = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(90))
    defense_date = factory.LazyAttribute(
        lambda o: o.submission_date + timedelta(days=random.randint(30, 90))
    )
    
    keywords = factory.LazyAttribute(lambda o: BaseFactory.random_research_keywords())
    
    # Statistics
    page_count = factory.LazyAttribute(lambda o: {
        "phd": random.randint(150, 300),
        "masters": random.randint(80, 150),
        "undergraduate": random.randint(40, 80),
    }[o.thesis_type])
    
    word_count = factory.LazyAttribute(lambda o: o.page_count * random.randint(250, 400))
    
    figure_count = factory.LazyAttribute(lambda o: random.randint(15, 50))
    table_count = factory.LazyAttribute(lambda o: random.randint(5, 20))
    equation_count = factory.LazyAttribute(lambda o: random.randint(10, 100))
    reference_count = factory.LazyAttribute(lambda o: {
        "phd": random.randint(100, 300),
        "masters": random.randint(50, 150),
        "undergraduate": random.randint(20, 50),
    }[o.thesis_type])


class AcademicContentFactory(DictFactory):
    """Factory for general academic content."""
    
    id = factory.Sequence(lambda n: f"content_{n}")
    
    content_type = factory.LazyAttribute(
        lambda o: random.choice([
            "research_proposal", "literature_review", "poster",
            "lab_report", "case_study", "white_paper"
        ])
    )
    
    title = factory.LazyAttribute(lambda o: academic_fake.research_title())
    
    # Content structure based on type
    structure = factory.LazyAttribute(lambda o: _generate_academic_structure(o.content_type))
    
    # Metadata
    field = factory.LazyAttribute(lambda o: BaseFactory.random_department())
    level = factory.LazyAttribute(
        lambda o: random.choice(["undergraduate", "graduate", "professional"])
    )
    
    keywords = factory.LazyAttribute(lambda o: BaseFactory.random_research_keywords())
    
    # Quality metrics
    completeness = factory.LazyAttribute(lambda o: random.uniform(0.7, 1.0))
    accuracy = factory.LazyAttribute(lambda o: random.uniform(0.8, 1.0))
    originality = factory.LazyAttribute(lambda o: random.uniform(0.6, 0.95))


def _format_citation_apa(citation: Dict[str, Any]) -> str:
    """Format citation in APA style."""
    authors = citation["authors"]
    if len(authors) > 2:
        author_str = f"{authors[0]['last_name']}, {authors[0]['first_name'][0]}., et al."
    elif len(authors) == 2:
        author_str = f"{authors[0]['last_name']}, {authors[0]['first_name'][0]}., & {authors[1]['last_name']}, {authors[1]['first_name'][0]}."
    else:
        author_str = f"{authors[0]['last_name']}, {authors[0]['first_name'][0]}."
    
    return f"{author_str} ({citation['year']}). {citation['title']}. {citation.get('journal', 'Unknown Journal')}"


def _format_citation_mla(citation: Dict[str, Any]) -> str:
    """Format citation in MLA style."""
    author = citation["authors"][0]
    return f"{author['last_name']}, {author['first_name']}. \"{citation['title']}.\" {citation.get('journal', 'Unknown Journal')} ({citation['year']})"


def _format_citation_chicago(citation: Dict[str, Any]) -> str:
    """Format citation in Chicago style."""
    author = citation["authors"][0]
    return f"{author['last_name']}, {author['first_name']}. \"{citation['title']}.\" {citation.get('journal', 'Unknown Journal')} ({citation['year']})"


def _format_citation_ieee(citation: Dict[str, Any]) -> str:
    """Format citation in IEEE style."""
    authors = citation["authors"]
    if len(authors) > 2:
        author_str = f"{authors[0]['first_name'][0]}. {authors[0]['last_name']} et al."
    else:
        author_str = f"{authors[0]['first_name'][0]}. {authors[0]['last_name']}"
    
    return f"{author_str}, \"{citation['title']},\" {citation.get('journal', 'Unknown Journal')}, {citation['year']}"


def _format_citation_bibtex(citation: Dict[str, Any]) -> str:
    """Format citation in BibTeX."""
    cite_key = f"{citation['authors'][0]['last_name'].lower()}{citation['year']}"
    return f"""@article{{{cite_key},
  author = {{{' and '.join([f"{a['last_name']}, {a['first_name']}" for a in citation['authors']])}}},
  title = {{{citation['title']}}},
  journal = {{{citation.get('journal', 'Unknown Journal')}}},
  year = {{{citation['year']}}}
}}"""


def _generate_thesis_chapters(thesis_type: str) -> List[Dict[str, Any]]:
    """Generate thesis chapters based on type."""
    base_chapters = [
        {
            "number": 1,
            "title": "Introduction",
            "sections": [
                "Background and Motivation",
                "Problem Statement",
                "Research Questions",
                "Contributions",
                "Thesis Organization"
            ],
        },
        {
            "number": 2,
            "title": "Literature Review",
            "sections": [
                "Theoretical Background",
                "Related Work",
                "Research Gap",
                "Summary"
            ],
        },
    ]
    
    if thesis_type == "phd":
        base_chapters.extend([
            {
                "number": 3,
                "title": "Theoretical Framework",
                "sections": [
                    "Mathematical Foundations",
                    "Proposed Model",
                    "Theoretical Analysis",
                    "Proofs and Derivations"
                ],
            },
            {
                "number": 4,
                "title": "Methodology",
                "sections": [
                    "Research Design",
                    "Data Collection",
                    "Experimental Setup",
                    "Evaluation Metrics"
                ],
            },
            {
                "number": 5,
                "title": "Implementation",
                "sections": [
                    "System Architecture",
                    "Algorithm Design",
                    "Technical Details",
                    "Optimization"
                ],
            },
            {
                "number": 6,
                "title": "Experimental Results",
                "sections": [
                    "Experimental Setup",
                    "Results and Analysis",
                    "Comparison with Baselines",
                    "Statistical Significance"
                ],
            },
            {
                "number": 7,
                "title": "Discussion",
                "sections": [
                    "Interpretation of Results",
                    "Implications",
                    "Limitations",
                    "Future Directions"
                ],
            },
            {
                "number": 8,
                "title": "Conclusions",
                "sections": [
                    "Summary of Contributions",
                    "Impact and Applications",
                    "Future Work",
                    "Final Remarks"
                ],
            },
        ])
    else:
        base_chapters.extend([
            {
                "number": 3,
                "title": "Methodology",
                "sections": [
                    "Research Approach",
                    "Data and Methods",
                    "Analysis Plan"
                ],
            },
            {
                "number": 4,
                "title": "Results and Discussion",
                "sections": [
                    "Findings",
                    "Analysis",
                    "Discussion"
                ],
            },
            {
                "number": 5,
                "title": "Conclusion",
                "sections": [
                    "Summary",
                    "Contributions",
                    "Future Work"
                ],
            },
        ])
    
    return base_chapters


def _generate_academic_structure(content_type: str) -> Dict[str, Any]:
    """Generate structure based on academic content type."""
    structures = {
        "research_proposal": {
            "sections": [
                "Abstract",
                "Introduction",
                "Literature Review",
                "Research Questions",
                "Methodology",
                "Timeline",
                "Expected Outcomes",
                "Budget",
                "References"
            ],
        },
        "literature_review": {
            "sections": [
                "Introduction",
                "Search Strategy",
                "Theoretical Background",
                "Thematic Analysis",
                "Critical Evaluation",
                "Research Gaps",
                "Conclusions",
                "References"
            ],
        },
        "poster": {
            "sections": [
                "Title",
                "Authors and Affiliations",
                "Abstract",
                "Introduction",
                "Methods",
                "Results",
                "Conclusions",
                "References",
                "Acknowledgments"
            ],
            "layout": "vertical",
            "dimensions": "36x48 inches",
        },
        "lab_report": {
            "sections": [
                "Title",
                "Abstract",
                "Introduction",
                "Materials and Methods",
                "Results",
                "Discussion",
                "Conclusions",
                "References",
                "Appendices"
            ],
        },
        "case_study": {
            "sections": [
                "Executive Summary",
                "Introduction",
                "Background",
                "Case Description",
                "Analysis",
                "Findings",
                "Recommendations",
                "Implementation Plan",
                "Conclusions"
            ],
        },
        "white_paper": {
            "sections": [
                "Executive Summary",
                "Introduction",
                "Problem Statement",
                "Proposed Solution",
                "Technical Details",
                "Benefits and Challenges",
                "Implementation Strategy",
                "Conclusions",
                "References"
            ],
        },
    }
    
    return structures.get(content_type, structures["research_proposal"])