"""
Mixed workload performance testing.

Simulates realistic user behavior with a mix of operations:
browsing, generating, editing, exporting, and collaborating.
"""
from locust import task, events, between
import random
import logging
from enum import Enum
from typing import Optional, List, Dict

from ..base_user import BaseSlideGenieUser
from ..config import config
from ..utils import generate_test_data, measure_time, metrics


logger = logging.getLogger(__name__)


class UserPersona(Enum):
    """Different user personas with different behavior patterns."""
    BROWSER = "browser"  # Mostly browsing and viewing
    CREATOR = "creator"  # Active content creation
    COLLABORATOR = "collaborator"  # Team collaboration focus
    POWER_USER = "power_user"  # Heavy usage of all features
    REVIEWER = "reviewer"  # Reviewing and commenting


class MixedWorkloadUser(BaseSlideGenieUser):
    """User that performs mixed operations simulating real usage."""
    
    wait_time = between(2, 8)  # More realistic wait times
    
    def on_start(self):
        """Initialize user with a persona."""
        super().on_start()
        
        # Assign user persona with weighted probability
        persona_weights = {
            UserPersona.BROWSER: 30,
            UserPersona.CREATOR: 25,
            UserPersona.COLLABORATOR: 20,
            UserPersona.POWER_USER: 10,
            UserPersona.REVIEWER: 15
        }
        
        self.persona = random.choices(
            list(persona_weights.keys()),
            weights=list(persona_weights.values())
        )[0]
        
        logger.info(f"User {self.user_id} assigned persona: {self.persona.value}")
        
        # Initialize user state
        self.current_presentation_id: Optional[str] = None
        self.favorite_templates: List[str] = []
        self.recent_searches: List[str] = []
        self.collaboration_rooms: List[str] = []
        
        # Fetch initial data
        self._initialize_user_data()
        
    def _initialize_user_data(self):
        """Fetch initial data based on persona."""
        # Get templates
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/templates",
            name="Get templates (init)"
        )
        
        if response.status_code == 200:
            templates = response.json().get("items", [])
            # Select favorite templates based on persona
            num_favorites = 3 if self.persona == UserPersona.POWER_USER else 1
            self.favorite_templates = [
                t["id"] for t in random.sample(templates, min(num_favorites, len(templates)))
            ]
            
        # Get user's presentations
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/my",
            name="Get my presentations"
        )
        
        if response.status_code == 200:
            presentations = response.json().get("items", [])
            if presentations:
                # Power users and creators have more presentations
                if self.persona in [UserPersona.POWER_USER, UserPersona.CREATOR]:
                    self.presentation_ids.extend([p["id"] for p in presentations])
                else:
                    # Others just keep a few recent ones
                    self.presentation_ids.extend([p["id"] for p in presentations[:3]])
                    
    # Browser persona tasks
    @task(10)
    def browse_templates(self):
        """Browse available templates."""
        if self.persona not in [UserPersona.BROWSER, UserPersona.CREATOR]:
            return
            
        # Browse with filters
        filters = random.choice([
            {},
            {"category": "academic"},
            {"category": "research"},
            {"tags": "conference"},
            {"sort": "popular"}
        ])
        
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/templates",
            name="Browse templates",
            params=filters
        )
        
        if response.status_code == 200:
            templates = response.json().get("items", [])
            
            # View template details for some
            if templates:
                num_to_view = random.randint(1, min(3, len(templates)))
                for template in random.sample(templates, num_to_view):
                    self._view_template_details(template["id"])
                    
    @task(8)
    def search_presentations(self):
        """Search for presentations."""
        search_query = generate_test_data.search_query()
        self.recent_searches.append(search_query)
        
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/search",
            name="Search presentations",
            params={
                "q": search_query,
                "limit": 20,
                "include_shared": True
            }
        )
        
        if response.status_code == 200:
            results = response.json().get("items", [])
            metrics.record_metric("search_results_count", len(results))
            
            # View some results
            if results and self.persona != UserPersona.BROWSER:
                for result in results[:2]:
                    self._view_presentation(result["id"])
                    
    # Creator persona tasks
    @task(5)
    def create_new_presentation(self):
        """Create a new presentation from scratch."""
        if self.persona not in [UserPersona.CREATOR, UserPersona.POWER_USER]:
            return
            
        template_id = random.choice(self.favorite_templates) if self.favorite_templates else "default"
        
        # Start with basic creation
        presentation_id = self.create_presentation(
            title=generate_test_data.presentation_title(),
            template_id=template_id
        )
        
        if presentation_id:
            self.current_presentation_id = presentation_id
            
            # Add initial content
            self._add_presentation_content(presentation_id)
            
            # Maybe generate with AI
            if random.random() < 0.5:
                self._generate_ai_content(presentation_id)
                
    @task(3)
    def upload_and_convert(self):
        """Upload document and convert to presentation."""
        if self.persona not in [UserPersona.CREATOR, UserPersona.POWER_USER]:
            return
            
        # Upload a document
        file_type = random.choice(["pdf", "docx"])
        file_path = config.sample_pdf_path if file_type == "pdf" else config.sample_docx_path
        
        upload_id = self.upload_file(file_path, file_type)
        
        if upload_id:
            # Wait for processing
            result = self.wait_for_job_completion(upload_id, "document-processing", timeout=120)
            
            if result.get("status") == "completed":
                # Convert to presentation
                self._convert_to_presentation(upload_id)
                
    # Collaborator persona tasks
    @task(6)
    def join_collaboration(self):
        """Join or create collaboration session."""
        if self.persona not in [UserPersona.COLLABORATOR, UserPersona.POWER_USER]:
            return
            
        if self.presentation_ids and random.random() < 0.7:
            # Join existing presentation
            presentation_id = random.choice(self.presentation_ids)
            self._start_collaboration(presentation_id)
        else:
            # Create new collaborative presentation
            presentation_id = self.create_presentation(
                title=f"Team Project - {generate_test_data.random_string(5)}",
                template_id=random.choice(self.favorite_templates) if self.favorite_templates else "default"
            )
            
            if presentation_id:
                self._start_collaboration(presentation_id)
                self._invite_collaborators(presentation_id)
                
    @task(4)
    def edit_slides(self):
        """Edit existing slides."""
        if not self.current_presentation_id:
            if self.presentation_ids:
                self.current_presentation_id = random.choice(self.presentation_ids)
            else:
                return
                
        # Get slides
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/{self.current_presentation_id}/slides",
            name="Get slides for editing"
        )
        
        if response.status_code == 200:
            slides = response.json().get("items", [])
            
            if slides:
                # Edit 1-3 slides
                slides_to_edit = random.sample(slides, min(random.randint(1, 3), len(slides)))
                
                for slide in slides_to_edit:
                    self._edit_slide(self.current_presentation_id, slide["id"])
                    
    # Power user tasks
    @task(2)
    def bulk_operations(self):
        """Perform bulk operations."""
        if self.persona != UserPersona.POWER_USER:
            return
            
        operation = random.choice(["bulk_create", "bulk_export", "bulk_delete"])
        
        if operation == "bulk_create":
            # Create multiple presentations at once
            num_presentations = random.randint(3, 5)
            for i in range(num_presentations):
                self.create_presentation(
                    title=f"Bulk Creation {i+1} - {generate_test_data.random_string(5)}",
                    template_id=random.choice(self.favorite_templates) if self.favorite_templates else "default"
                )
                
        elif operation == "bulk_export" and len(self.presentation_ids) >= 3:
            # Export multiple presentations
            presentations_to_export = random.sample(self.presentation_ids, 3)
            format = random.choice(["pdf", "pptx"])
            
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/export/bulk",
                name=f"Bulk export to {format}",
                json={
                    "presentation_ids": presentations_to_export,
                    "format": format
                }
            )
            
            if response.status_code == 202:
                bulk_job_id = response.json().get("bulk_job_id")
                self.wait_for_job_completion(bulk_job_id, "export/bulk", timeout=300)
                
    @task(3)
    def advanced_features(self):
        """Use advanced features."""
        if self.persona not in [UserPersona.POWER_USER, UserPersona.CREATOR]:
            return
            
        if not self.current_presentation_id:
            return
            
        feature = random.choice([
            "ai_suggestions",
            "style_customization",
            "analytics",
            "version_history"
        ])
        
        if feature == "ai_suggestions":
            self._get_ai_suggestions(self.current_presentation_id)
        elif feature == "style_customization":
            self._customize_style(self.current_presentation_id)
        elif feature == "analytics":
            self._view_analytics(self.current_presentation_id)
        elif feature == "version_history":
            self._view_version_history(self.current_presentation_id)
            
    # Reviewer persona tasks
    @task(4)
    def review_and_comment(self):
        """Review presentations and add comments."""
        if self.persona not in [UserPersona.REVIEWER, UserPersona.COLLABORATOR]:
            return
            
        # Get shared presentations
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/shared",
            name="Get shared presentations"
        )
        
        if response.status_code == 200:
            shared_presentations = response.json().get("items", [])
            
            if shared_presentations:
                presentation = random.choice(shared_presentations)
                self._review_presentation(presentation["id"])
                
    # Common tasks for all personas
    @task(15)
    def view_presentation(self):
        """View a presentation (common task)."""
        if self.presentation_ids:
            presentation_id = random.choice(self.presentation_ids)
            self._view_presentation(presentation_id)
            
    @task(5)
    def export_presentation(self):
        """Export a presentation."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        format = self._choose_export_format()
        
        self.export_presentation(presentation_id, format)
        
    @task(3)
    def manage_account(self):
        """Manage account settings."""
        action = random.choice([
            "view_profile",
            "update_preferences",
            "check_usage",
            "manage_api_keys"
        ])
        
        if action == "view_profile":
            self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/users/me",
                name="View profile"
            )
        elif action == "update_preferences":
            self.make_authenticated_request(
                "patch",
                f"{config.api_prefix}/users/me/preferences",
                name="Update preferences",
                json={
                    "theme": random.choice(["light", "dark", "auto"]),
                    "language": random.choice(["en", "es", "fr", "de"]),
                    "notifications_enabled": random.choice([True, False])
                }
            )
        elif action == "check_usage":
            self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/users/me/usage",
                name="Check usage stats"
            )
        elif action == "manage_api_keys" and self.persona == UserPersona.POWER_USER:
            self._manage_api_keys()
            
    # Helper methods
    def _view_template_details(self, template_id: str):
        """View template details."""
        self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/templates/{template_id}",
            name="View template details"
        )
        
    def _view_presentation(self, presentation_id: str):
        """View a presentation with slides."""
        # Get presentation details
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/{presentation_id}",
            name="View presentation"
        )
        
        if response.status_code == 200:
            # Get slides
            self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/presentations/{presentation_id}/slides",
                name="Get presentation slides"
            )
            
            # Record view event
            self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/analytics/events",
                name="Record view event",
                json={
                    "event": "presentation_viewed",
                    "presentation_id": presentation_id,
                    "duration": random.randint(10, 300)
                }
            )
            
    def _add_presentation_content(self, presentation_id: str):
        """Add content to presentation."""
        # Add 5-10 slides
        num_slides = random.randint(5, 10)
        
        for i in range(num_slides):
            slide_data = generate_test_data.slide_content()
            slide_data["position"] = i + 1
            
            self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/presentations/{presentation_id}/slides",
                name="Add slide",
                json=slide_data
            )
            
    def _generate_ai_content(self, presentation_id: str):
        """Generate content using AI."""
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/generation/enhance",
            name="AI content generation",
            json={
                "presentation_id": presentation_id,
                "options": {
                    "enhance_content": True,
                    "add_speaker_notes": True,
                    "improve_flow": True
                }
            }
        )
        
        if response.status_code == 202:
            job_id = response.json().get("job_id")
            self.wait_for_job_completion(job_id, "generation", timeout=180)
            
    def _convert_to_presentation(self, upload_id: str):
        """Convert uploaded document to presentation."""
        template_id = random.choice(self.favorite_templates) if self.favorite_templates else "default"
        
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/generation/from-document",
            name="Convert to presentation",
            json={
                "upload_id": upload_id,
                "template_id": template_id,
                "options": {
                    "extract_images": True,
                    "maintain_formatting": True
                }
            }
        )
        
        if response.status_code == 202:
            job_id = response.json().get("job_id")
            result = self.wait_for_job_completion(job_id, "generation", timeout=300)
            
            if result.get("status") == "completed":
                presentation_id = result.get("presentation_id")
                if presentation_id:
                    self.presentation_ids.append(presentation_id)
                    self.current_presentation_id = presentation_id
                    
    def _start_collaboration(self, presentation_id: str):
        """Start collaboration session."""
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/realtime/sessions",
            name="Start collaboration",
            json={
                "presentation_id": presentation_id,
                "type": "collaboration"
            }
        )
        
        if response.status_code == 201:
            session_id = response.json().get("session_id")
            self.collaboration_rooms.append(session_id)
            
    def _invite_collaborators(self, presentation_id: str):
        """Invite collaborators to presentation."""
        num_invites = random.randint(1, 3)
        
        for _ in range(num_invites):
            self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/presentations/{presentation_id}/share",
                name="Share presentation",
                json={
                    "email": fake.email(),
                    "role": random.choice(["viewer", "editor", "reviewer"]),
                    "message": "Please review this presentation"
                }
            )
            
    def _edit_slide(self, presentation_id: str, slide_id: str):
        """Edit a slide."""
        updates = generate_test_data.slide_content()
        
        self.make_authenticated_request(
            "patch",
            f"{config.api_prefix}/presentations/{presentation_id}/slides/{slide_id}",
            name="Edit slide",
            json=updates
        )
        
    def _get_ai_suggestions(self, presentation_id: str):
        """Get AI suggestions for presentation."""
        self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/generation/suggestions",
            name="Get AI suggestions",
            json={
                "presentation_id": presentation_id,
                "suggestion_types": ["content", "design", "flow"]
            }
        )
        
    def _customize_style(self, presentation_id: str):
        """Customize presentation style."""
        self.make_authenticated_request(
            "patch",
            f"{config.api_prefix}/presentations/{presentation_id}/style",
            name="Customize style",
            json={
                "theme": random.choice(["professional", "academic", "creative", "minimal"]),
                "color_scheme": random.choice(["blue", "green", "purple", "custom"]),
                "font_family": random.choice(["Arial", "Helvetica", "Times", "Calibri"])
            }
        )
        
    def _view_analytics(self, presentation_id: str):
        """View presentation analytics."""
        self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/analytics/presentations/{presentation_id}",
            name="View analytics"
        )
        
    def _view_version_history(self, presentation_id: str):
        """View version history."""
        self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/{presentation_id}/versions",
            name="View version history"
        )
        
    def _review_presentation(self, presentation_id: str):
        """Review and comment on presentation."""
        # View the presentation first
        self._view_presentation(presentation_id)
        
        # Add comments to random slides
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/presentations/{presentation_id}/slides",
            name="Get slides for review"
        )
        
        if response.status_code == 200:
            slides = response.json().get("items", [])
            
            # Comment on 2-4 slides
            slides_to_comment = random.sample(
                slides,
                min(random.randint(2, 4), len(slides))
            )
            
            for slide in slides_to_comment:
                self.make_authenticated_request(
                    "post",
                    f"{config.api_prefix}/presentations/{presentation_id}/slides/{slide['id']}/comments",
                    name="Add comment",
                    json={
                        "text": fake.sentence(),
                        "type": random.choice(["suggestion", "question", "approval"])
                    }
                )
                
    def _choose_export_format(self) -> str:
        """Choose export format based on persona."""
        if self.persona == UserPersona.POWER_USER:
            return random.choice(["pptx", "pdf", "beamer", "google-slides"])
        elif self.persona == UserPersona.CREATOR:
            return random.choice(["pptx", "pdf"])
        else:
            return "pdf"
            
    def _manage_api_keys(self):
        """Manage API keys (power users only)."""
        action = random.choice(["list", "create", "revoke"])
        
        if action == "list":
            self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/users/me/api-keys",
                name="List API keys"
            )
        elif action == "create":
            self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/users/me/api-keys",
                name="Create API key",
                json={
                    "name": f"Test Key {generate_test_data.random_string(5)}",
                    "scopes": ["read", "write"]
                }
            )


# Import faker
from faker import Faker
fake = Faker()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export mixed workload metrics."""
    import os
    from datetime import datetime
    
    results_dir = "tests/performance/results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics.export_to_file(f"{results_dir}/mixed_workload_metrics_{timestamp}.json")
    
    # Print persona distribution
    print("\n=== Mixed Workload Performance Summary ===")
    print("\nUser Persona Distribution:")
    # This would need to be tracked during the test run