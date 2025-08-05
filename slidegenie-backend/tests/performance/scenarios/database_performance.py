"""
Database performance testing.

Tests database query optimization, connection pooling, transaction throughput,
and complex query performance under load.
"""
from locust import task, events, constant_pacing
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..base_user import BaseSlideGenieUser
from ..config import config
from ..utils import generate_test_data, measure_time, metrics


logger = logging.getLogger(__name__)


class DatabasePerformanceUser(BaseSlideGenieUser):
    """User that performs database-intensive operations."""
    
    wait_time = constant_pacing(0.5)  # 2 requests per second
    
    def on_start(self):
        """Set up test data for database operations."""
        super().on_start()
        
        # Create initial test data
        self._create_test_data()
        
        # Store query patterns
        self.complex_filters = self._generate_complex_filters()
        self.search_terms = [generate_test_data.search_query() for _ in range(20)]
        
    def _create_test_data(self):
        """Create test data for database queries."""
        # Create presentations with various attributes
        for i in range(10):
            presentation_id = self.create_presentation(
                title=generate_test_data.presentation_title(),
                template_id="default"
            )
            
            if presentation_id:
                # Add slides with content for full-text search
                self._add_searchable_content(presentation_id)
                
                # Add tags for filtering
                self._add_tags(presentation_id)
                
                # Share with random users for join queries
                if random.random() < 0.5:
                    self._share_presentation(presentation_id)
                    
    def _add_searchable_content(self, presentation_id: str):
        """Add content that will be used in search queries."""
        slides_data = []
        
        for i in range(random.randint(10, 20)):
            slide = generate_test_data.slide_content()
            slide["position"] = i + 1
            
            # Add keywords for search testing
            keywords = random.sample(self.search_terms, random.randint(1, 3))
            slide["content"] = f"{slide['content']} {' '.join(keywords)}"
            
            slides_data.append(slide)
            
        self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/presentations/{presentation_id}/slides/bulk",
            name="Add searchable slides",
            json={"slides": slides_data}
        )
        
    def _add_tags(self, presentation_id: str):
        """Add tags for filtering tests."""
        tags = random.sample([
            "research", "academic", "conference", "tutorial",
            "workshop", "thesis", "report", "proposal",
            "machine-learning", "data-science", "physics",
            "biology", "chemistry", "mathematics"
        ], random.randint(2, 5))
        
        self.make_authenticated_request(
            "patch",
            f"{config.api_prefix}/presentations/{presentation_id}",
            name="Add tags",
            json={"tags": tags}
        )
        
    def _share_presentation(self, presentation_id: str):
        """Share presentation to test join queries."""
        num_shares = random.randint(1, 5)
        
        for _ in range(num_shares):
            self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/presentations/{presentation_id}/share",
                name="Share for joins",
                json={
                    "email": generate_test_data.user_data()["email"],
                    "role": random.choice(["viewer", "editor"])
                }
            )
            
    def _generate_complex_filters(self) -> List[Dict[str, Any]]:
        """Generate complex filter combinations."""
        return [
            # Date range queries
            {
                "created_after": (datetime.now() - timedelta(days=30)).isoformat(),
                "created_before": datetime.now().isoformat()
            },
            # Multi-field filters
            {
                "tags": ["research", "academic"],
                "has_collaborators": True,
                "min_slides": 10
            },
            # Sorting with pagination
            {
                "sort_by": "updated_at",
                "sort_order": "desc",
                "limit": 20,
                "offset": 0
            },
            # Complex boolean queries
            {
                "tags_any": ["machine-learning", "data-science"],
                "tags_all": ["academic"],
                "exclude_tags": ["draft"]
            }
        ]
        
    @task(15)
    def simple_queries(self):
        """Perform simple database queries."""
        query_type = random.choice([
            "get_by_id",
            "list_recent",
            "count_total",
            "check_exists"
        ])
        
        if query_type == "get_by_id" and self.presentation_ids:
            # Simple primary key lookup
            presentation_id = random.choice(self.presentation_ids)
            
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations/{presentation_id}",
                    name="Get by ID (DB)"
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_simple_get", timer.duration_ms)
                
        elif query_type == "list_recent":
            # List with simple ordering
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations",
                    name="List recent (DB)",
                    params={"limit": 10, "sort": "created_at_desc"}
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_list_recent", timer.duration_ms)
                
        elif query_type == "count_total":
            # Count query
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations/count",
                    name="Count total (DB)"
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_count", timer.duration_ms)
                
        elif query_type == "check_exists":
            # Existence check
            if self.presentation_ids:
                presentation_id = random.choice(self.presentation_ids)
                
                with measure_time() as timer:
                    response = self.make_authenticated_request(
                        "head",
                        f"{config.api_prefix}/presentations/{presentation_id}",
                        name="Check exists (DB)"
                    )
                    
                if response.status_code in [200, 204]:
                    metrics.record_metric("db_query_exists", timer.duration_ms)
                    
    @task(10)
    def complex_filters(self):
        """Perform queries with complex filters."""
        filter_set = random.choice(self.complex_filters)
        
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/presentations",
                name="Complex filter (DB)",
                params=filter_set
            )
            
        if response.status_code == 200:
            result_count = len(response.json().get("items", []))
            metrics.record_metric("db_query_complex_filter", timer.duration_ms)
            metrics.record_metric("db_query_result_count", result_count)
            
    @task(8)
    def full_text_search(self):
        """Perform full-text search queries."""
        search_term = random.choice(self.search_terms)
        
        search_params = {
            "q": search_term,
            "search_in": random.choice(["all", "title", "content", "notes"]),
            "limit": 20
        }
        
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/presentations/search",
                name="Full-text search (DB)",
                params=search_params
            )
            
        if response.status_code == 200:
            metrics.record_metric("db_query_fulltext_search", timer.duration_ms)
            
            # Test search with highlighting
            if random.random() < 0.3:
                search_params["highlight"] = True
                
                with measure_time() as highlight_timer:
                    response = self.make_authenticated_request(
                        "get",
                        f"{config.api_prefix}/presentations/search",
                        name="Search with highlight (DB)",
                        params=search_params
                    )
                    
                if response.status_code == 200:
                    metrics.record_metric("db_query_search_highlight", highlight_timer.duration_ms)
                    
    @task(5)
    def aggregation_queries(self):
        """Perform aggregation queries."""
        aggregation_type = random.choice([
            "stats_by_user",
            "tags_frequency",
            "activity_timeline",
            "collaboration_metrics"
        ])
        
        if aggregation_type == "stats_by_user":
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/analytics/user-stats",
                    name="User stats aggregation (DB)"
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_user_stats", timer.duration_ms)
                
        elif aggregation_type == "tags_frequency":
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/analytics/tags/frequency",
                    name="Tags frequency (DB)"
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_tags_frequency", timer.duration_ms)
                
        elif aggregation_type == "activity_timeline":
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/analytics/activity",
                    name="Activity timeline (DB)",
                    params={
                        "interval": "day",
                        "days": 30
                    }
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_activity_timeline", timer.duration_ms)
                
        elif aggregation_type == "collaboration_metrics":
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/analytics/collaboration",
                    name="Collaboration metrics (DB)"
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_collaboration_metrics", timer.duration_ms)
                
    @task(3)
    def join_heavy_queries(self):
        """Perform queries with multiple joins."""
        if not self.presentation_ids:
            return
            
        query_type = random.choice([
            "with_collaborators",
            "with_full_details",
            "shared_with_me"
        ])
        
        if query_type == "with_collaborators":
            # Query presentations with all collaborator details
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations",
                    name="With collaborators (DB)",
                    params={
                        "include": "collaborators,owner,shared_users",
                        "has_collaborators": True
                    }
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_with_collaborators", timer.duration_ms)
                
        elif query_type == "with_full_details":
            # Query with all related data
            presentation_id = random.choice(self.presentation_ids)
            
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations/{presentation_id}/full",
                    name="Full details with joins (DB)"
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_full_details", timer.duration_ms)
                
        elif query_type == "shared_with_me":
            # Complex query for shared presentations
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations/shared-with-me",
                    name="Shared with me (DB)",
                    params={
                        "include_indirect": True,
                        "group_by": "owner"
                    }
                )
                
            if response.status_code == 200:
                metrics.record_metric("db_query_shared_complex", timer.duration_ms)
                
    @task(2)
    def pagination_stress(self):
        """Test pagination with large offsets."""
        # Test different pagination strategies
        strategy = random.choice(["offset", "cursor", "keyset"])
        
        if strategy == "offset":
            # Traditional offset pagination
            offset = random.choice([0, 100, 500, 1000, 5000])
            
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations",
                    name=f"Offset pagination (DB) - {offset}",
                    params={
                        "limit": 20,
                        "offset": offset
                    }
                )
                
            if response.status_code == 200:
                metrics.record_metric(f"db_query_pagination_offset_{offset}", timer.duration_ms)
                
        elif strategy == "cursor":
            # Cursor-based pagination
            response = self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/presentations",
                name="Cursor pagination start (DB)",
                params={"limit": 20, "use_cursor": True}
            )
            
            if response.status_code == 200:
                cursor = response.json().get("next_cursor")
                
                # Follow cursor for a few pages
                for i in range(random.randint(2, 5)):
                    if not cursor:
                        break
                        
                    with measure_time() as timer:
                        response = self.make_authenticated_request(
                            "get",
                            f"{config.api_prefix}/presentations",
                            name=f"Cursor pagination page {i+2} (DB)",
                            params={
                                "cursor": cursor,
                                "limit": 20
                            }
                        )
                        
                    if response.status_code == 200:
                        metrics.record_metric("db_query_pagination_cursor", timer.duration_ms)
                        cursor = response.json().get("next_cursor")
                        
    @task(4)
    def concurrent_writes(self):
        """Test concurrent write operations."""
        operation = random.choice([
            "bulk_insert",
            "bulk_update",
            "concurrent_updates"
        ])
        
        if operation == "bulk_insert":
            # Bulk insert slides
            if self.presentation_ids:
                presentation_id = random.choice(self.presentation_ids)
                slides_data = [generate_test_data.slide_content() for _ in range(10)]
                
                with measure_time() as timer:
                    response = self.make_authenticated_request(
                        "post",
                        f"{config.api_prefix}/presentations/{presentation_id}/slides/bulk",
                        name="Bulk insert (DB)",
                        json={"slides": slides_data}
                    )
                    
                if response.status_code == 201:
                    metrics.record_metric("db_write_bulk_insert", timer.duration_ms)
                    
        elif operation == "bulk_update":
            # Bulk update presentations
            if len(self.presentation_ids) >= 3:
                presentations_to_update = random.sample(self.presentation_ids, 3)
                
                with measure_time() as timer:
                    response = self.make_authenticated_request(
                        "patch",
                        f"{config.api_prefix}/presentations/bulk",
                        name="Bulk update (DB)",
                        json={
                            "presentation_ids": presentations_to_update,
                            "updates": {
                                "tags": ["bulk-updated"],
                                "metadata": {"bulk_update_time": datetime.now().isoformat()}
                            }
                        }
                    )
                    
                if response.status_code == 200:
                    metrics.record_metric("db_write_bulk_update", timer.duration_ms)
                    
        elif operation == "concurrent_updates":
            # Simulate concurrent updates to same resource
            if self.presentation_ids:
                presentation_id = random.choice(self.presentation_ids)
                
                # Multiple rapid updates
                for i in range(3):
                    with measure_time() as timer:
                        response = self.make_authenticated_request(
                            "patch",
                            f"{config.api_prefix}/presentations/{presentation_id}",
                            name="Concurrent update (DB)",
                            json={
                                "metadata": {
                                    f"update_{i}": datetime.now().isoformat(),
                                    "random_value": random.random()
                                }
                            }
                        )
                        
                    if response.status_code == 200:
                        metrics.record_metric("db_write_concurrent_update", timer.duration_ms)
                        
    @task(1)
    def transaction_stress(self):
        """Test transactional operations."""
        # Complex operation that requires transaction
        presentation_data = {
            "title": generate_test_data.presentation_title(),
            "template_id": "default",
            "slides": [generate_test_data.slide_content() for _ in range(20)],
            "collaborators": [generate_test_data.user_data()["email"] for _ in range(3)],
            "tags": random.sample(["tag1", "tag2", "tag3", "tag4", "tag5"], 3)
        }
        
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/presentations/create-complete",
                name="Transactional create (DB)",
                json=presentation_data
            )
            
        if response.status_code == 201:
            metrics.record_metric("db_transaction_complete_create", timer.duration_ms)
            presentation_id = response.json().get("id")
            if presentation_id:
                self.presentation_ids.append(presentation_id)
                
    @task(2)
    def cache_effectiveness(self):
        """Test cache effectiveness with repeated queries."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        
        # First query (potential cache miss)
        with measure_time() as timer1:
            response1 = self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/presentations/{presentation_id}",
                name="Cache test - first (DB)"
            )
            
        if response1.status_code == 200:
            metrics.record_metric("db_cache_first_query", timer1.duration_ms)
            
            # Immediate second query (should hit cache)
            with measure_time() as timer2:
                response2 = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/presentations/{presentation_id}",
                    name="Cache test - second (DB)"
                )
                
            if response2.status_code == 200:
                metrics.record_metric("db_cache_second_query", timer2.duration_ms)
                
                # Calculate cache effectiveness
                if timer1.duration_ms > 0:
                    cache_speedup = timer1.duration_ms / timer2.duration_ms
                    metrics.record_metric("db_cache_speedup_ratio", cache_speedup)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export database performance metrics."""
    import os
    from datetime import datetime
    
    results_dir = "tests/performance/results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics.export_to_file(f"{results_dir}/database_metrics_{timestamp}.json")
    
    # Print database performance summary
    summary = metrics.get_summary()
    print("\n=== Database Performance Summary ===")
    
    # Query performance by type
    query_types = [
        ("Simple Get", "db_query_simple_get"),
        ("Complex Filter", "db_query_complex_filter"),
        ("Full-text Search", "db_query_fulltext_search"),
        ("Aggregation", "db_query_user_stats"),
        ("Join Heavy", "db_query_with_collaborators"),
        ("Bulk Write", "db_write_bulk_insert")
    ]
    
    for name, metric_key in query_types:
        if metric_key in summary["metrics"]:
            query_metrics = summary["metrics"][metric_key]
            print(f"\n{name}:")
            print(f"  Count: {query_metrics['count']}")
            print(f"  P50: {query_metrics['p50']:.2f}ms")
            print(f"  P90: {query_metrics['p90']:.2f}ms")
            print(f"  P95: {query_metrics['p95']:.2f}ms")
            print(f"  Max: {query_metrics['max']:.2f}ms")