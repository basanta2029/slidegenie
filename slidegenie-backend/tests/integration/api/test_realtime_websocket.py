"""
Integration tests for real-time WebSocket connections.

Tests WebSocket communication, real-time updates, collaboration features,
and presence tracking.
"""
import asyncio
import json
from typing import List
from uuid import uuid4

import pytest
import websockets
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketConnection:
    """Test WebSocket connection and communication."""
    
    async def test_websocket_connection(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
    ):
        """Test establishing WebSocket connection with authentication."""
        # Get WebSocket URL from client base URL
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        ws_url = f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send ping
            await websocket.send(json.dumps({
                "type": "ping",
                "id": str(uuid4()),
            }))
            
            # Receive pong
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "pong"
    
    async def test_websocket_authentication_required(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that WebSocket requires authentication."""
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        ws_url = f"{ws_url}/api/v1/ws"
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url):
                pass
        
        assert exc_info.value.status_code == 401
    
    async def test_websocket_invalid_token(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test WebSocket with invalid token."""
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        ws_url = f"{ws_url}/api/v1/ws?token=invalid_token"
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url):
                pass
        
        assert exc_info.value.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
class TestRealtimeUpdates:
    """Test real-time presentation updates."""
    
    async def test_presentation_update_broadcast(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
        test_user,
        db_session,
    ):
        """Test broadcasting presentation updates to connected clients."""
        # Create presentation
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": "Realtime Test",
                "slides": [],
            },
        )
        presentation_id = response.json()["id"]
        
        # Connect two WebSocket clients
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as ws1, websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as ws2:
            
            # Subscribe both clients to presentation updates
            subscribe_msg = {
                "type": "subscribe",
                "channel": f"presentation:{presentation_id}",
                "id": str(uuid4()),
            }
            
            await ws1.send(json.dumps(subscribe_msg))
            await ws2.send(json.dumps(subscribe_msg))
            
            # Wait for subscription confirmations
            await ws1.recv()
            await ws2.recv()
            
            # Update presentation via API
            await authenticated_client.put(
                f"/api/v1/presentations/{presentation_id}",
                json={
                    "title": "Updated Realtime Test",
                    "slides": [
                        {
                            "type": "title",
                            "title": "New Slide",
                            "content": {},
                            "order": 1,
                        }
                    ],
                },
            )
            
            # Both clients should receive update
            update1 = json.loads(await ws1.recv())
            update2 = json.loads(await ws2.recv())
            
            assert update1["type"] == "presentation:updated"
            assert update1["data"]["id"] == presentation_id
            assert update1["data"]["title"] == "Updated Realtime Test"
            
            assert update2["type"] == "presentation:updated"
            assert update2["data"]["id"] == presentation_id
    
    async def test_slide_update_notification(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
    ):
        """Test real-time notifications for slide updates."""
        # Create presentation with slides
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": "Slide Update Test",
                "slides": [
                    {
                        "type": "title",
                        "title": "Original Title",
                        "content": {},
                        "order": 1,
                    }
                ],
            },
        )
        presentation = response.json()
        presentation_id = presentation["id"]
        slide_id = presentation["slides"][0]["id"]
        
        # Connect WebSocket
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as websocket:
            
            # Subscribe to presentation
            await websocket.send(json.dumps({
                "type": "subscribe",
                "channel": f"presentation:{presentation_id}",
                "id": str(uuid4()),
            }))
            
            await websocket.recv()  # Subscription confirmation
            
            # Update slide
            await authenticated_client.put(
                f"/api/v1/presentations/{presentation_id}/slides/{slide_id}",
                json={
                    "title": "Updated Title",
                    "content": {"subtitle": "New subtitle"},
                },
            )
            
            # Receive update notification
            update = json.loads(await websocket.recv())
            
            assert update["type"] == "slide:updated"
            assert update["data"]["slide_id"] == slide_id
            assert update["data"]["title"] == "Updated Title"
    
    async def test_generation_progress_updates(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
        test_presentation_data,
        mock_ai_responses,
    ):
        """Test real-time progress updates during generation."""
        # Connect WebSocket
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as websocket:
            
            # Start generation
            response = await authenticated_client.post(
                "/api/v1/presentations/generate",
                json=test_presentation_data,
            )
            job_id = response.json()["job_id"]
            
            # Subscribe to job updates
            await websocket.send(json.dumps({
                "type": "subscribe",
                "channel": f"job:{job_id}",
                "id": str(uuid4()),
            }))
            
            await websocket.recv()  # Subscription confirmation
            
            # Collect progress updates
            updates = []
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    update = json.loads(message)
                    
                    if update["type"] == "job:progress":
                        updates.append(update["data"]["progress"])
                    elif update["type"] == "job:completed":
                        break
                    
                except asyncio.TimeoutError:
                    break
                
                # Prevent infinite loop
                if asyncio.get_event_loop().time() - start_time > 30:
                    break
            
            # Verify progress updates
            assert len(updates) > 0
            assert all(0 <= p <= 100 for p in updates)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCollaborationFeatures:
    """Test real-time collaboration features."""
    
    async def test_presence_tracking(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
        test_user,
        admin_user,
        token_service,
    ):
        """Test user presence tracking in presentations."""
        # Create presentation
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={"title": "Collaboration Test", "slides": []},
        )
        presentation_id = response.json()["id"]
        
        # Create tokens for admin user
        admin_tokens = await token_service.create_token_pair(
            user_id=admin_user.id,
            email=admin_user.email,
            roles=[admin_user.role],
            institution=admin_user.institution,
        )
        
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        
        # Connect two users
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as ws_user, websockets.connect(
            f"{ws_url}/api/v1/ws?token={admin_tokens.access_token}"
        ) as ws_admin:
            
            # Both users join presentation
            join_msg = {
                "type": "join",
                "channel": f"presentation:{presentation_id}",
                "id": str(uuid4()),
            }
            
            await ws_user.send(json.dumps(join_msg))
            await ws_admin.send(json.dumps(join_msg))
            
            # Collect presence updates
            messages = []
            for _ in range(4):  # Expect join confirmations and presence updates
                try:
                    msg1 = json.loads(await asyncio.wait_for(ws_user.recv(), timeout=2))
                    messages.append(msg1)
                except asyncio.TimeoutError:
                    pass
            
            # Verify presence updates
            presence_updates = [m for m in messages if m["type"] == "presence:update"]
            assert len(presence_updates) > 0
            
            # Check active users
            active_users = presence_updates[-1]["data"]["users"]
            assert len(active_users) == 2
            assert any(u["id"] == str(test_user.id) for u in active_users)
            assert any(u["id"] == str(admin_user.id) for u in active_users)
    
    async def test_cursor_position_sync(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
    ):
        """Test cursor position synchronization between users."""
        # Create presentation
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={"title": "Cursor Sync Test", "slides": []},
        )
        presentation_id = response.json()["id"]
        
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        
        # Connect two sessions
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as ws1, websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as ws2:
            
            # Join presentation
            join_msg = {
                "type": "join",
                "channel": f"presentation:{presentation_id}",
                "id": str(uuid4()),
            }
            
            await ws1.send(json.dumps(join_msg))
            await ws2.send(json.dumps(join_msg))
            
            # Clear join messages
            await ws1.recv()
            await ws2.recv()
            
            # Send cursor position from ws1
            cursor_msg = {
                "type": "cursor:move",
                "data": {
                    "slide_id": "slide_1",
                    "x": 100,
                    "y": 200,
                },
                "id": str(uuid4()),
            }
            
            await ws1.send(json.dumps(cursor_msg))
            
            # ws2 should receive cursor update
            update = json.loads(await ws2.recv())
            
            assert update["type"] == "cursor:update"
            assert update["data"]["x"] == 100
            assert update["data"]["y"] == 200
    
    async def test_collaborative_editing_lock(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
        test_user,
        admin_user,
        token_service,
    ):
        """Test slide locking for collaborative editing."""
        # Create presentation with slides
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": "Lock Test",
                "slides": [
                    {"type": "title", "title": "Slide 1", "content": {}, "order": 1},
                    {"type": "content", "title": "Slide 2", "content": {}, "order": 2},
                ],
            },
        )
        presentation = response.json()
        presentation_id = presentation["id"]
        slide_id = presentation["slides"][0]["id"]
        
        # Create admin client
        admin_tokens = await token_service.create_token_pair(
            user_id=admin_user.id,
            email=admin_user.email,
            roles=[admin_user.role],
            institution=admin_user.institution,
        )
        
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}"
        ) as ws_user, websockets.connect(
            f"{ws_url}/api/v1/ws?token={admin_tokens.access_token}"
        ) as ws_admin:
            
            # Join presentation
            join_msg = {
                "type": "join",
                "channel": f"presentation:{presentation_id}",
                "id": str(uuid4()),
            }
            
            await ws_user.send(json.dumps(join_msg))
            await ws_admin.send(json.dumps(join_msg))
            
            # Clear join messages
            await ws_user.recv()
            await ws_admin.recv()
            
            # User locks slide for editing
            lock_msg = {
                "type": "slide:lock",
                "data": {"slide_id": slide_id},
                "id": str(uuid4()),
            }
            
            await ws_user.send(json.dumps(lock_msg))
            
            # Both should receive lock notification
            lock_update1 = json.loads(await ws_user.recv())
            lock_update2 = json.loads(await ws_admin.recv())
            
            assert lock_update1["type"] == "slide:locked"
            assert lock_update1["data"]["slide_id"] == slide_id
            assert lock_update1["data"]["locked_by"] == str(test_user.id)
            
            # Admin tries to lock same slide
            await ws_admin.send(json.dumps(lock_msg))
            
            # Should receive error
            error_msg = json.loads(await ws_admin.recv())
            assert error_msg["type"] == "error"
            assert "locked" in error_msg["data"]["message"].lower()
            
            # User unlocks slide
            unlock_msg = {
                "type": "slide:unlock",
                "data": {"slide_id": slide_id},
                "id": str(uuid4()),
            }
            
            await ws_user.send(json.dumps(unlock_msg))
            
            # Both should receive unlock notification
            unlock_update1 = json.loads(await ws_user.recv())
            unlock_update2 = json.loads(await ws_admin.recv())
            
            assert unlock_update1["type"] == "slide:unlocked"
            assert unlock_update1["data"]["slide_id"] == slide_id


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketReconnection:
    """Test WebSocket reconnection and state recovery."""
    
    async def test_reconnection_with_same_session(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
    ):
        """Test reconnecting with same session ID."""
        ws_url = str(authenticated_client.base_url).replace("http://", "ws://")
        session_id = str(uuid4())
        
        # First connection
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}&session_id={session_id}"
        ) as ws1:
            # Subscribe to test channel
            await ws1.send(json.dumps({
                "type": "subscribe",
                "channel": "test:channel",
                "id": str(uuid4()),
            }))
            
            await ws1.recv()  # Subscription confirmation
        
        # Reconnect with same session ID
        async with websockets.connect(
            f"{ws_url}/api/v1/ws?token={auth_tokens.access_token}&session_id={session_id}"
        ) as ws2:
            # Should restore subscriptions
            await ws2.send(json.dumps({
                "type": "ping",
                "id": str(uuid4()),
            }))
            
            response = json.loads(await ws2.recv())
            assert response["type"] == "pong"
            
            # Verify subscription was restored
            await ws2.send(json.dumps({
                "type": "get_subscriptions",
                "id": str(uuid4()),
            }))
            
            subs_response = json.loads(await ws2.recv())
            assert "test:channel" in subs_response["data"]["channels"]
    
    async def test_message_queue_during_disconnect(
        self,
        authenticated_client: AsyncClient,
        auth_tokens,
    ):
        """Test message queuing during temporary disconnect."""
        # This would require more complex infrastructure to test properly
        # Including Redis pub/sub and message persistence
        # Marking as a placeholder for now
        pass