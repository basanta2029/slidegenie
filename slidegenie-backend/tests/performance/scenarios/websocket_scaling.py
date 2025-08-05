"""
WebSocket connection scaling and real-time collaboration testing.

Tests WebSocket connection limits, message throughput, and real-time
collaboration features under load.
"""
import json
import time
import random
import logging
from typing import Optional, Dict, Any
from locust import User, task, events, between
from websocket import create_connection, WebSocket
import websocket

from ..config import config
from ..utils import generate_test_data, measure_time, metrics


logger = logging.getLogger(__name__)


class WebSocketUser(User):
    """User that maintains WebSocket connections."""
    
    wait_time = between(0.5, 2)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws: Optional[WebSocket] = None
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.presentation_id: Optional[str] = None
        self.room_id: Optional[str] = None
        self.message_count = 0
        self.last_heartbeat = time.time()
        
    def on_start(self):
        """Authenticate and establish WebSocket connection."""
        # First authenticate via HTTP
        self._authenticate()
        
        # Then connect WebSocket
        self._connect_websocket()
        
        # Join a collaboration room
        self._join_collaboration_room()
        
    def on_stop(self):
        """Clean up WebSocket connection."""
        if self.ws:
            try:
                # Leave room
                if self.room_id:
                    self._send_message({
                        "type": "leave_room",
                        "room_id": self.room_id
                    })
                    
                # Close connection
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
                
    def _authenticate(self):
        """Authenticate via HTTP to get token."""
        import requests
        
        response = requests.post(
            f"{config.base_url}{config.api_prefix}/auth/login",
            json={
                "email": config.test_user_email,
                "password": config.test_user_password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            
            # Record auth success
            events.request.fire(
                request_type="HTTP",
                name="WebSocket Auth",
                response_time=response.elapsed.total_seconds() * 1000,
                response_length=len(response.content),
                response=response,
                exception=None,
                context={}
            )
        else:
            raise Exception(f"Authentication failed: {response.text}")
            
    def _connect_websocket(self):
        """Establish WebSocket connection."""
        ws_url = f"{config.websocket_url}{config.api_prefix}/ws"
        
        # Add auth token to URL
        ws_url += f"?token={self.auth_token}"
        
        start_time = time.time()
        try:
            self.ws = create_connection(
                ws_url,
                timeout=30,
                header={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            connection_time = (time.time() - start_time) * 1000
            
            # Record successful connection
            events.request.fire(
                request_type="WebSocket",
                name="Connect",
                response_time=connection_time,
                response_length=0,
                response=None,
                exception=None,
                context={}
            )
            
            metrics.record_metric("websocket_connection_time", connection_time)
            
            # Start heartbeat
            self._start_heartbeat()
            
        except Exception as e:
            connection_time = (time.time() - start_time) * 1000
            
            # Record failed connection
            events.request.fire(
                request_type="WebSocket",
                name="Connect",
                response_time=connection_time,
                response_length=0,
                response=None,
                exception=e,
                context={}
            )
            
            metrics.record_error("websocket_connection_failed")
            raise
            
    def _join_collaboration_room(self):
        """Join or create a collaboration room."""
        # Try to join an existing room or create new one
        room_type = random.choice(["presentation", "team", "review"])
        
        if room_type == "presentation":
            # Create a presentation and join its room
            self.presentation_id = self._create_presentation()
            if self.presentation_id:
                self.room_id = f"presentation:{self.presentation_id}"
        else:
            # Join a team or review room
            self.room_id = f"{room_type}:{generate_test_data.random_string(10)}"
            
        # Send join room message
        self._send_message({
            "type": "join_room",
            "room_id": self.room_id,
            "user_info": {
                "id": self.user_id,
                "name": f"Test User {self.user_id[:8]}"
            }
        })
        
    def _create_presentation(self) -> Optional[str]:
        """Create a presentation via HTTP for collaboration."""
        import requests
        
        response = requests.post(
            f"{config.base_url}{config.api_prefix}/presentations",
            headers={"Authorization": f"Bearer {self.auth_token}"},
            json={
                "title": generate_test_data.presentation_title(),
                "template_id": "default-academic"
            }
        )
        
        if response.status_code == 201:
            return response.json().get("id")
        return None
        
    def _start_heartbeat(self):
        """Start periodic heartbeat."""
        self.last_heartbeat = time.time()
        
    def _send_heartbeat(self):
        """Send heartbeat message."""
        if time.time() - self.last_heartbeat > config.websocket_heartbeat_interval:
            self._send_message({"type": "ping"})
            self.last_heartbeat = time.time()
            
    def _send_message(self, message: Dict[str, Any]):
        """Send a message through WebSocket."""
        if not self.ws:
            return
            
        try:
            with measure_time() as timer:
                self.ws.send(json.dumps(message))
                self.message_count += 1
                
            # Record message send time
            events.request.fire(
                request_type="WebSocket",
                name=f"Send {message.get('type', 'unknown')}",
                response_time=timer.duration_ms,
                response_length=len(json.dumps(message)),
                response=None,
                exception=None,
                context={}
            )
            
            metrics.record_metric(f"websocket_send_{message.get('type', 'unknown')}", 
                                timer.duration_ms)
            
        except Exception as e:
            events.request.fire(
                request_type="WebSocket",
                name=f"Send {message.get('type', 'unknown')}",
                response_time=0,
                response_length=0,
                response=None,
                exception=e,
                context={}
            )
            
            metrics.record_error(f"websocket_send_failed_{message.get('type', 'unknown')}")
            
    def _receive_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Receive a message from WebSocket."""
        if not self.ws:
            return None
            
        try:
            self.ws.settimeout(timeout)
            with measure_time() as timer:
                data = self.ws.recv()
                
            message = json.loads(data) if data else None
            
            if message:
                # Record message receive time
                events.request.fire(
                    request_type="WebSocket",
                    name=f"Receive {message.get('type', 'unknown')}",
                    response_time=timer.duration_ms,
                    response_length=len(data),
                    response=None,
                    exception=None,
                    context={}
                )
                
                metrics.record_metric(f"websocket_receive_{message.get('type', 'unknown')}", 
                                    timer.duration_ms)
                
            return message
            
        except websocket.WebSocketTimeoutException:
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None
            
    @task(10)
    def send_cursor_position(self):
        """Send cursor position update (high frequency)."""
        if not self.room_id:
            return
            
        self._send_message({
            "type": "cursor_move",
            "room_id": self.room_id,
            "data": {
                "slide_id": random.randint(1, 20),
                "x": random.uniform(0, 1920),
                "y": random.uniform(0, 1080)
            }
        })
        
    @task(5)
    def send_slide_edit(self):
        """Send slide content edit."""
        if not self.room_id or not self.presentation_id:
            return
            
        self._send_message({
            "type": "slide_edit",
            "room_id": self.room_id,
            "data": {
                "presentation_id": self.presentation_id,
                "slide_id": random.randint(1, 20),
                "changes": {
                    "title": generate_test_data.random_string(20),
                    "content": generate_test_data.random_string(100)
                }
            }
        })
        
    @task(3)
    def send_chat_message(self):
        """Send chat message in collaboration."""
        if not self.room_id:
            return
            
        self._send_message({
            "type": "chat",
            "room_id": self.room_id,
            "data": {
                "message": fake.sentence(),
                "timestamp": time.time()
            }
        })
        
    @task(2)
    def request_slide_lock(self):
        """Request to lock a slide for editing."""
        if not self.room_id or not self.presentation_id:
            return
            
        slide_id = random.randint(1, 20)
        
        # Request lock
        self._send_message({
            "type": "lock_request",
            "room_id": self.room_id,
            "data": {
                "presentation_id": self.presentation_id,
                "slide_id": slide_id,
                "lock_type": "edit"
            }
        })
        
        # Simulate editing
        time.sleep(random.uniform(2, 5))
        
        # Release lock
        self._send_message({
            "type": "lock_release",
            "room_id": self.room_id,
            "data": {
                "presentation_id": self.presentation_id,
                "slide_id": slide_id
            }
        })
        
    @task(1)
    def broadcast_notification(self):
        """Send broadcast notification."""
        if not self.room_id:
            return
            
        self._send_message({
            "type": "notification",
            "room_id": self.room_id,
            "data": {
                "level": random.choice(["info", "warning", "success"]),
                "message": fake.sentence(),
                "target": "all"  # Broadcast to all users
            }
        })
        
    @task(15)
    def receive_messages(self):
        """Receive and process messages."""
        # Receive up to 10 messages
        for _ in range(10):
            message = self._receive_message(timeout=0.1)
            if message:
                self._process_message(message)
            else:
                break
                
        # Send heartbeat if needed
        self._send_heartbeat()
        
    @task(1)
    def simulate_reconnection(self):
        """Simulate connection drop and reconnection."""
        if not self.ws:
            return
            
        # Close current connection
        try:
            self.ws.close()
        except:
            pass
            
        # Record disconnection
        metrics.record_metric("websocket_disconnection", 1)
        
        # Wait a bit
        time.sleep(random.uniform(1, 3))
        
        # Reconnect
        try:
            self._connect_websocket()
            
            # Rejoin room
            if self.room_id:
                self._send_message({
                    "type": "rejoin_room",
                    "room_id": self.room_id,
                    "last_message_id": self.message_count
                })
                
            metrics.record_metric("websocket_reconnection_success", 1)
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            metrics.record_error("websocket_reconnection_failed")
            
    def _process_message(self, message: Dict[str, Any]):
        """Process received message."""
        msg_type = message.get("type")
        
        if msg_type == "pong":
            # Calculate round-trip time
            if "timestamp" in message:
                rtt = (time.time() - message["timestamp"]) * 1000
                metrics.record_metric("websocket_rtt", rtt)
                
        elif msg_type == "slide_update":
            # Someone else updated a slide
            metrics.record_metric("collaborative_update_received", 1)
            
        elif msg_type == "user_joined":
            # New user joined room
            metrics.record_metric("room_user_count", message.get("user_count", 0))
            
        elif msg_type == "error":
            # Server error
            metrics.record_error(f"websocket_server_error_{message.get('code', 'unknown')}")


# Import faker for chat messages
from faker import Faker
fake = Faker()


class WebSocketStressUser(WebSocketUser):
    """User that creates stress conditions for WebSocket server."""
    
    wait_time = between(0.1, 0.5)  # Much more aggressive
    
    @task(20)
    def rapid_fire_messages(self):
        """Send many messages rapidly."""
        if not self.room_id:
            return
            
        # Send 10-20 messages in rapid succession
        for _ in range(random.randint(10, 20)):
            self._send_message({
                "type": "stress_test",
                "room_id": self.room_id,
                "data": {
                    "payload": generate_test_data.random_string(1000),
                    "sequence": self.message_count
                }
            })
            
    @task(5)
    def large_message(self):
        """Send very large messages."""
        if not self.room_id:
            return
            
        # Send 100KB - 1MB message
        size_kb = random.randint(100, 1000)
        large_payload = generate_test_data.generate_large_text(size_kb)
        
        self._send_message({
            "type": "large_payload",
            "room_id": self.room_id,
            "data": {
                "content": large_payload,
                "size_kb": size_kb
            }
        })
        
        metrics.record_metric("websocket_large_message_size_kb", size_kb)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export WebSocket metrics."""
    import os
    from datetime import datetime
    
    results_dir = "tests/performance/results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics.export_to_file(f"{results_dir}/websocket_metrics_{timestamp}.json")
    
    # Print WebSocket performance summary
    summary = metrics.get_summary()
    print("\n=== WebSocket Performance Summary ===")
    
    if "websocket_connection_time" in summary["metrics"]:
        conn_metrics = summary["metrics"]["websocket_connection_time"]
        print(f"\nConnection Time:")
        print(f"  P50: {conn_metrics['p50']:.2f}ms")
        print(f"  P90: {conn_metrics['p90']:.2f}ms")
        print(f"  P95: {conn_metrics['p95']:.2f}ms")
        
    if "websocket_rtt" in summary["metrics"]:
        rtt_metrics = summary["metrics"]["websocket_rtt"]
        print(f"\nRound-Trip Time:")
        print(f"  P50: {rtt_metrics['p50']:.2f}ms")
        print(f"  P90: {rtt_metrics['p90']:.2f}ms")
        print(f"  P95: {rtt_metrics['p95']:.2f}ms")