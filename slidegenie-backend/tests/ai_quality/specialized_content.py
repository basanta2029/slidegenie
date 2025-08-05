"""
Specialized Content Testing Module.

Tests specialized academic content including mathematical equations,
code snippets, chemical formulas, diagrams, and tables.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import structlog
import sympy
from sympy.parsing.latex import parse_latex

logger = structlog.get_logger(__name__)


@dataclass
class SpecializedContentResult:
    """Result of specialized content verification."""
    equation_accuracy: float
    code_validity: float
    formula_accuracy: float
    diagram_quality: float
    table_integrity: float
    issues: List[Dict[str, Any]]
    verified_content: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class SpecializedContentTest:
    """Tests specialized academic content types."""
    
    def __init__(self):
        # Mathematical equation patterns
        self.equation_patterns = {
            "latex": r'\$([^$]+)\$|\$\$([^$]+)\$\$',
            "unicode": r'[∑∏∫∂∇⊗⊕∈∉⊆⊇∀∃]',
            "ascii_math": r'(?:sum|prod|int|sqrt|frac|lim)[\s\(]',
        }
        
        # Code language detection patterns
        self.code_patterns = {
            "python": r'(?:def|class|import|from|if\s+__name__|print\()',
            "javascript": r'(?:function|const|let|var|=&gt;|console\.log)',
            "java": r'(?:public\s+class|private\s+void|System\.out\.println)',
            "r": r'(?:library\(|ggplot\(|data\.frame|&lt;-)',
            "matlab": r'(?:function\s+\[|end\s*;|plot\(|zeros\()',
        }
        
        # Chemical formula patterns
        self.chemical_patterns = {
            "molecular": r'[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*',
            "ionic": r'[A-Z][a-z]?\d*[+-]\d*',
            "structural": r'(?:CH3|OH|NH2|COOH|C=O)',
            "reaction": r'(?:→|⟶|&lt;-&gt;|⇌)',
        }
        
        # Table structure patterns
        self.table_patterns = {
            "markdown": r'\|[^|]+\|',
            "html": r'&lt;table.*?&gt;.*?&lt;/table&gt;',
            "latex": r'\\begin\{tabular\}.*?\\end\{tabular\}',
        }
    
    def verify(self, content: Dict[str, Any]) -> SpecializedContentResult:
        """
        Verify specialized content accuracy.
        
        Args:
            content: Content to verify including slides
            
        Returns:
            SpecializedContentResult with detailed verification
        """
        slides = content.get("slides", [])
        
        # Verify different content types
        equation_score, equation_issues, verified_equations = self._verify_equations(slides)
        code_score, code_issues, verified_code = self._verify_code(slides)
        formula_score, formula_issues, verified_formulas = self._verify_chemical_formulas(slides)
        diagram_score, diagram_issues = self._assess_diagrams(slides)
        table_score, table_issues, verified_tables = self._verify_tables(slides)
        
        # Combine all issues
        all_issues = (
            equation_issues + code_issues + formula_issues +
            diagram_issues + table_issues
        )
        
        # Combine verified content
        all_verified = verified_equations + verified_code + verified_formulas + verified_tables
        
        return SpecializedContentResult(
            equation_accuracy=equation_score,
            code_validity=code_score,
            formula_accuracy=formula_score,
            diagram_quality=diagram_score,
            table_integrity=table_score,
            issues=all_issues,
            verified_content=all_verified,
            metadata={
                "equation_count": len(verified_equations),
                "code_snippet_count": len(verified_code),
                "formula_count": len(verified_formulas),
                "table_count": len(verified_tables),
            }
        )
    
    def _verify_equations(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Verify mathematical equations."""
        issues = []
        verified = []
        equations = self._extract_equations(slides)
        
        if not equations:
            return 1.0, [], []
        
        valid_count = 0
        
        for eq in equations:
            validation = self._validate_equation(eq)
            
            if validation["valid"]:
                valid_count += 1
                verified.append({
                    "type": "equation",
                    "content": eq["content"],
                    "format": eq["format"],
                    "slide_number": eq["slide_number"],
                    "parsed": validation.get("parsed"),
                })
            else:
                issues.append({
                    "type": "invalid_equation",
                    "severity": validation["severity"],
                    "slide_number": eq["slide_number"],
                    "description": validation["description"],
                    "suggestion": validation["suggestion"],
                    "content": eq["content"][:50] + "...",
                })
        
        score = valid_count / len(equations) if equations else 1.0
        
        return score, issues, verified
    
    def _verify_code(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Verify code snippets."""
        issues = []
        verified = []
        code_snippets = self._extract_code_snippets(slides)
        
        if not code_snippets:
            return 1.0, [], []
        
        valid_count = 0
        
        for snippet in code_snippets:
            validation = self._validate_code_snippet(snippet)
            
            if validation["valid"]:
                valid_count += 1
                verified.append({
                    "type": "code",
                    "language": snippet["language"],
                    "content": snippet["content"],
                    "slide_number": snippet["slide_number"],
                    "syntax_valid": True,
                })
            else:
                issues.append({
                    "type": "invalid_code",
                    "severity": validation["severity"],
                    "slide_number": snippet["slide_number"],
                    "description": validation["description"],
                    "suggestion": validation["suggestion"],
                    "language": snippet["language"],
                })
        
        score = valid_count / len(code_snippets) if code_snippets else 1.0
        
        return score, issues, verified
    
    def _verify_chemical_formulas(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Verify chemical formulas."""
        issues = []
        verified = []
        formulas = self._extract_chemical_formulas(slides)
        
        if not formulas:
            return 1.0, [], []
        
        valid_count = 0
        
        for formula in formulas:
            validation = self._validate_chemical_formula(formula)
            
            if validation["valid"]:
                valid_count += 1
                verified.append({
                    "type": "chemical_formula",
                    "content": formula["content"],
                    "formula_type": formula["type"],
                    "slide_number": formula["slide_number"],
                    "balanced": validation.get("balanced", True),
                })
            else:
                issues.append({
                    "type": "invalid_formula",
                    "severity": validation["severity"],
                    "slide_number": formula["slide_number"],
                    "description": validation["description"],
                    "suggestion": validation["suggestion"],
                })
        
        score = valid_count / len(formulas) if formulas else 1.0
        
        return score, issues, verified
    
    def _assess_diagrams(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]]]:
        """Assess diagram descriptions and quality."""
        issues = []
        diagrams = self._extract_diagrams(slides)
        
        if not diagrams:
            return 1.0, []
        
        quality_scores = []
        
        for diagram in diagrams:
            assessment = self._assess_diagram_quality(diagram)
            quality_scores.append(assessment["score"])
            
            if assessment["issues"]:
                for issue in assessment["issues"]:
                    issues.append({
                        "type": "diagram_issue",
                        "severity": issue["severity"],
                        "slide_number": diagram["slide_number"],
                        "description": issue["description"],
                        "suggestion": issue["suggestion"],
                    })
        
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 1.0
        
        return avg_score, issues
    
    def _verify_tables(self, slides: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Verify table data integrity."""
        issues = []
        verified = []
        tables = self._extract_tables(slides)
        
        if not tables:
            return 1.0, [], []
        
        valid_count = 0
        
        for table in tables:
            validation = self._validate_table(table)
            
            if validation["valid"]:
                valid_count += 1
                verified.append({
                    "type": "table",
                    "content": table["content"],
                    "format": table["format"],
                    "slide_number": table["slide_number"],
                    "rows": validation.get("rows", 0),
                    "columns": validation.get("columns", 0),
                })
            else:
                issues.append({
                    "type": "invalid_table",
                    "severity": validation["severity"],
                    "slide_number": table["slide_number"],
                    "description": validation["description"],
                    "suggestion": validation["suggestion"],
                })
        
        score = valid_count / len(tables) if tables else 1.0
        
        return score, issues, verified
    
    def _extract_equations(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract mathematical equations from slides."""
        equations = []
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            # LaTeX equations
            latex_matches = re.findall(self.equation_patterns["latex"], content)
            for match in latex_matches:
                eq_content = match[0] or match[1]  # Single $ or double $$
                if eq_content:
                    equations.append({
                        "content": eq_content,
                        "format": "latex",
                        "slide_number": i + 1,
                    })
            
            # Unicode math symbols
            if re.search(self.equation_patterns["unicode"], content):
                # Extract surrounding context
                unicode_eqs = re.findall(r'[^.!?]*[∑∏∫∂∇⊗⊕∈∉⊆⊇∀∃][^.!?]*', content)
                for eq in unicode_eqs:
                    equations.append({
                        "content": eq.strip(),
                        "format": "unicode",
                        "slide_number": i + 1,
                    })
            
            # ASCII math notation
            if re.search(self.equation_patterns["ascii_math"], content):
                ascii_eqs = re.findall(r'[^.!?]*(?:sum|prod|int|sqrt|frac|lim)[^.!?]*', content)
                for eq in ascii_eqs:
                    equations.append({
                        "content": eq.strip(),
                        "format": "ascii",
                        "slide_number": i + 1,
                    })
        
        return equations
    
    def _validate_equation(self, equation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a mathematical equation."""
        content = equation["content"]
        format_type = equation["format"]
        
        if format_type == "latex":
            try:
                # Try to parse LaTeX
                parsed = parse_latex(content)
                
                # Check for common issues
                if '\\frac' in content and not re.search(r'\\frac\{[^}]+\}\{[^}]+\}', content):
                    return {
                        "valid": False,
                        "severity": "major",
                        "description": "Malformed fraction in LaTeX",
                        "suggestion": "Use \\frac{numerator}{denominator}",
                    }
                
                # Check for balanced brackets
                if content.count('{') != content.count('}'):
                    return {
                        "valid": False,
                        "severity": "critical",
                        "description": "Unbalanced brackets in LaTeX",
                        "suggestion": "Check that all { have matching }",
                    }
                
                return {"valid": True, "parsed": str(parsed)}
                
            except Exception as e:
                return {
                    "valid": False,
                    "severity": "major",
                    "description": f"Invalid LaTeX syntax: {str(e)}",
                    "suggestion": "Verify LaTeX equation syntax",
                }
        
        elif format_type == "unicode":
            # Check for proper use of unicode symbols
            if '∑' in content and not re.search(r'∑[^=]*=', content):
                return {
                    "valid": False,
                    "severity": "minor",
                    "description": "Summation symbol without bounds",
                    "suggestion": "Add summation bounds (e.g., ∑ᵢ₌₁ⁿ)",
                }
            
            return {"valid": True}
        
        else:  # ASCII math
            # Basic validation for ASCII math
            if 'sqrt(' in content and content.count('(') != content.count(')'):
                return {
                    "valid": False,
                    "severity": "major",
                    "description": "Unbalanced parentheses",
                    "suggestion": "Check parentheses matching",
                }
            
            return {"valid": True}
    
    def _extract_code_snippets(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract code snippets from slides."""
        snippets = []
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            # Look for code blocks (markdown style)
            code_blocks = re.findall(r'```(\w+)?\n?(.*?)```', content, re.DOTALL)
            for lang, code in code_blocks:
                snippets.append({
                    "content": code.strip(),
                    "language": lang or self._detect_language(code),
                    "slide_number": i + 1,
                })
            
            # Look for inline code patterns
            for lang, pattern in self.code_patterns.items():
                if re.search(pattern, content):
                    # Extract surrounding context as potential code
                    matches = re.findall(r'[^\n]*' + pattern + r'[^\n]*', content)
                    for match in matches:
                        if match not in [s["content"] for s in snippets]:
                            snippets.append({
                                "content": match.strip(),
                                "language": lang,
                                "slide_number": i + 1,
                            })
        
        return snippets
    
    def _validate_code_snippet(self, snippet: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a code snippet."""
        content = snippet["content"]
        language = snippet["language"]
        
        # Basic syntax validation by language
        if language == "python":
            # Check indentation
            lines = content.split('\n')
            indent_errors = []
            for i, line in enumerate(lines):
                if line.strip() and line[0] == ' ':
                    # Check if indentation is multiple of 4
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces % 4 != 0:
                        indent_errors.append(i + 1)
            
            if indent_errors:
                return {
                    "valid": False,
                    "severity": "major",
                    "description": f"Inconsistent indentation on lines: {indent_errors[:3]}",
                    "suggestion": "Use 4 spaces for Python indentation",
                }
            
            # Check for syntax errors
            try:
                compile(content, '<string>', 'exec')
                return {"valid": True}
            except SyntaxError as e:
                return {
                    "valid": False,
                    "severity": "critical",
                    "description": f"Python syntax error: {e.msg}",
                    "suggestion": f"Fix syntax error at line {e.lineno}",
                }
        
        elif language == "javascript":
            # Check for basic syntax issues
            if content.count('{') != content.count('}'):
                return {
                    "valid": False,
                    "severity": "critical",
                    "description": "Unbalanced curly braces",
                    "suggestion": "Check that all { have matching }",
                }
            
            if content.count('(') != content.count(')'):
                return {
                    "valid": False,
                    "severity": "critical",
                    "description": "Unbalanced parentheses",
                    "suggestion": "Check that all ( have matching )",
                }
            
            # Check for missing semicolons (warning only)
            lines = content.split('\n')
            for line in lines:
                if line.strip() and not line.strip().endswith((';', '{', '}', ',')):
                    if any(keyword in line for keyword in ['const', 'let', 'var', 'return']):
                        return {
                            "valid": True,  # Valid but with warning
                            "severity": "minor",
                            "description": "Missing semicolon (optional in JS)",
                            "suggestion": "Consider adding semicolons for consistency",
                        }
        
        # For other languages or if validation passes
        return {"valid": True}
    
    def _detect_language(self, code: str) -> str:
        """Detect programming language from code content."""
        for lang, pattern in self.code_patterns.items():
            if re.search(pattern, code):
                return lang
        return "unknown"
    
    def _extract_chemical_formulas(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract chemical formulas from slides."""
        formulas = []
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            # Skip if no chemistry-related content
            if not any(term in content.lower() for term in 
                      ["chemical", "molecule", "compound", "reaction", "element"]):
                continue
            
            # Molecular formulas
            molecular = re.findall(r'\b(' + self.chemical_patterns["molecular"] + r')\b', content)
            for formula in molecular:
                if self._is_chemical_formula(formula):
                    formulas.append({
                        "content": formula,
                        "type": "molecular",
                        "slide_number": i + 1,
                    })
            
            # Chemical reactions
            if re.search(self.chemical_patterns["reaction"], content):
                reactions = re.findall(r'([^.!?]*(?:→|⟶|&lt;-&gt;|⇌)[^.!?]*)', content)
                for reaction in reactions:
                    formulas.append({
                        "content": reaction.strip(),
                        "type": "reaction",
                        "slide_number": i + 1,
                    })
        
        return formulas
    
    def _is_chemical_formula(self, text: str) -> bool:
        """Check if text is likely a chemical formula."""
        # Common element symbols
        elements = [
            "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
            "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
            "Fe", "Cu", "Zn", "Ag", "Au", "Hg", "Pb"
        ]
        
        # Check if contains valid element symbols
        parts = re.findall(r'[A-Z][a-z]?', text)
        return any(part in elements for part in parts)
    
    def _validate_chemical_formula(self, formula: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a chemical formula."""
        content = formula["content"]
        formula_type = formula["type"]
        
        if formula_type == "molecular":
            # Check for valid element symbols
            if not self._is_chemical_formula(content):
                return {
                    "valid": False,
                    "severity": "major",
                    "description": "Invalid element symbols in formula",
                    "suggestion": "Verify element symbols are correct",
                }
            
            # Check subscript format
            if re.search(r'[A-Z][a-z]?\d{3,}', content):
                return {
                    "valid": False,
                    "severity": "minor",
                    "description": "Unusually large subscript in formula",
                    "suggestion": "Verify subscript numbers are correct",
                }
            
            return {"valid": True}
        
        elif formula_type == "reaction":
            # Check for balanced arrow
            if '→' in content or '->' in content:
                parts = re.split(r'→|->|⟶', content)
                if len(parts) != 2:
                    return {
                        "valid": False,
                        "severity": "major",
                        "description": "Malformed chemical reaction",
                        "suggestion": "Use format: reactants → products",
                    }
                
                # Basic check for reactants and products
                if not parts[0].strip() or not parts[1].strip():
                    return {
                        "valid": False,
                        "severity": "major",
                        "description": "Missing reactants or products",
                        "suggestion": "Include both reactants and products",
                    }
            
            return {"valid": True, "balanced": True}  # Simplified - real validation would check stoichiometry
        
        return {"valid": True}
    
    def _extract_diagrams(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract diagram descriptions from slides."""
        diagrams = []
        
        diagram_indicators = [
            "figure", "diagram", "chart", "graph", "plot",
            "illustration", "schematic", "flowchart"
        ]
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            # Look for diagram references
            for indicator in diagram_indicators:
                pattern = rf'{indicator}\s*\d*\s*:?\s*([^.!?\n]+)'
                matches = re.findall(pattern, content, re.I)
                for match in matches:
                    diagrams.append({
                        "description": match.strip(),
                        "type": indicator,
                        "slide_number": i + 1,
                    })
            
            # Check for explicit diagram metadata
            if slide.get("has_figure") or slide.get("has_chart"):
                diagrams.append({
                    "description": slide.get("figure_caption", ""),
                    "type": "figure",
                    "slide_number": i + 1,
                })
        
        return diagrams
    
    def _assess_diagram_quality(self, diagram: Dict[str, Any]) -> Dict[str, Any]:
        """Assess diagram description quality."""
        description = diagram["description"]
        issues = []
        score = 1.0
        
        # Check description length
        if len(description) < 20:
            issues.append({
                "severity": "major",
                "description": "Diagram description too brief",
                "suggestion": "Add more descriptive details about the diagram",
            })
            score -= 0.3
        
        # Check for key components
        key_components = ["shows", "illustrates", "depicts", "represents", "demonstrates"]
        if not any(comp in description.lower() for comp in key_components):
            issues.append({
                "severity": "minor",
                "description": "Diagram description lacks clear purpose",
                "suggestion": "Explain what the diagram shows or illustrates",
            })
            score -= 0.2
        
        # Check for data description (for charts/graphs)
        if diagram["type"] in ["chart", "graph", "plot"]:
            if not re.search(r'\b(?:axis|axes|x|y|data|values)\b', description, re.I):
                issues.append({
                    "severity": "major",
                    "description": "Chart/graph lacks axis or data description",
                    "suggestion": "Describe axes, data series, and units",
                })
                score -= 0.3
        
        return {
            "score": max(0.0, score),
            "issues": issues,
        }
    
    def _extract_tables(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tables from slides."""
        tables = []
        
        for i, slide in enumerate(slides):
            content = self._get_slide_content(slide)
            
            # Markdown tables
            if '|' in content:
                table_lines = [line for line in content.split('\n') if '|' in line]
                if len(table_lines) >= 3:  # Header + separator + at least one row
                    tables.append({
                        "content": '\n'.join(table_lines),
                        "format": "markdown",
                        "slide_number": i + 1,
                    })
            
            # Check for table indicators
            if slide.get("has_table") or "table" in content.lower():
                # Extract table caption or description
                table_match = re.search(r'table\s*\d*\s*:?\s*([^.!?\n]+)', content, re.I)
                if table_match:
                    tables.append({
                        "content": table_match.group(0),
                        "format": "reference",
                        "slide_number": i + 1,
                    })
        
        return tables
    
    def _validate_table(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """Validate table structure and data."""
        content = table["content"]
        format_type = table["format"]
        
        if format_type == "markdown":
            lines = content.strip().split('\n')
            
            # Check if all rows have same number of columns
            column_counts = []
            for line in lines:
                if '|' in line and '---' not in line:  # Skip separator line
                    columns = [col.strip() for col in line.split('|') if col.strip()]
                    column_counts.append(len(columns))
            
            if column_counts and len(set(column_counts)) > 1:
                return {
                    "valid": False,
                    "severity": "major",
                    "description": "Inconsistent column count in table",
                    "suggestion": "Ensure all rows have the same number of columns",
                }
            
            # Check for header separator
            if len(lines) >= 2 and '---' not in lines[1]:
                return {
                    "valid": False,
                    "severity": "minor",
                    "description": "Missing header separator in markdown table",
                    "suggestion": "Add separator line (e.g., |---|---|) after header",
                }
            
            return {
                "valid": True,
                "rows": len([l for l in lines if '|' in l and '---' not in l]),
                "columns": column_counts[0] if column_counts else 0,
            }
        
        # For reference tables, just check if description exists
        return {"valid": bool(content.strip())}
    
    def _get_slide_content(self, slide: Dict[str, Any]) -> str:
        """Extract all text content from a slide."""
        parts = []
        
        for key in ["title", "content", "bullet_points", "speaker_notes"]:
            if key in slide:
                if isinstance(slide[key], list):
                    parts.extend(str(item) for item in slide[key])
                elif slide[key]:
                    parts.append(str(slide[key]))
        
        return " ".join(parts)