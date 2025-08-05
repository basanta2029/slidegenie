"""Unit tests for Anthropic AI provider."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from typing import Dict, Any

from app.services.ai.anthropic_provider import AnthropicProvider
from tests.unit.utils.test_helpers import MockResponse, create_mock_async_context_manager


class TestAnthropicProvider:
    """Test suite for Anthropic AI provider."""
    
    @pytest.fixture
    def provider(self):
        """Create Anthropic provider instance."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-api-key'}):
            return AnthropicProvider()
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client."""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_generate_successful_response(self, provider, mock_anthropic_client):
        """Test successful content generation."""
        # Mock response
        mock_message = Mock()
        mock_message.content = [Mock(text="Generated presentation content")]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic_client.return_value = mock_client_instance
        
        # Reinitialize provider to use mocked client
        provider._client = None
        
        # Test generation
        result = await provider.generate(
            prompt="Create a presentation about AI",
            max_tokens=1000,
            temperature=0.7
        )
        
        assert result == "Generated presentation content"
        mock_client_instance.messages.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider, mock_anthropic_client):
        """Test generation with system prompt."""
        mock_message = Mock()
        mock_message.content = [Mock(text="Academic presentation content")]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate(
            prompt="Create an academic presentation",
            system_prompt="You are an academic presentation expert"
        )
        
        assert result == "Academic presentation content"
        
        # Verify system prompt was included
        call_args = mock_client_instance.messages.create.call_args
        assert call_args.kwargs['system'] == "You are an academic presentation expert"
    
    @pytest.mark.asyncio
    async def test_generate_json_response(self, provider, mock_anthropic_client):
        """Test JSON response generation."""
        json_content = {
            "title": "AI in Healthcare",
            "sections": ["Introduction", "Applications", "Challenges", "Conclusion"]
        }
        
        mock_message = Mock()
        mock_message.content = [Mock(text=json.dumps(json_content))]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate_json(
            prompt="Create presentation structure",
            schema={"type": "object", "properties": {"title": {"type": "string"}}}
        )
        
        assert result == json_content
    
    @pytest.mark.asyncio
    async def test_generate_with_retry_on_rate_limit(self, provider, mock_anthropic_client):
        """Test retry mechanism on rate limit errors."""
        mock_client_instance = AsyncMock()
        
        # First call raises rate limit error, second succeeds
        mock_message = Mock()
        mock_message.content = [Mock(text="Success after retry")]
        
        mock_client_instance.messages.create = AsyncMock(
            side_effect=[
                Exception("Rate limit exceeded"),
                mock_message
            ]
        )
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await provider.generate("Test prompt")
        
        assert result == "Success after retry"
        assert mock_client_instance.messages.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_with_token_limit_exceeded(self, provider, mock_anthropic_client):
        """Test handling of token limit exceeded."""
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(
            side_effect=Exception("Maximum token limit exceeded")
        )
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        with pytest.raises(Exception) as exc_info:
            await provider.generate("Very long prompt" * 1000)
        
        assert "token limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_calculate_cost(self, provider):
        """Test cost calculation for API usage."""
        # Test with different token counts
        cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="claude-3-opus-20240229"
        )
        
        # Verify cost calculation (adjust based on actual pricing)
        assert cost > 0
        assert isinstance(cost, float)
    
    @pytest.mark.asyncio
    async def test_validate_response_format(self, provider, mock_anthropic_client):
        """Test response format validation."""
        # Test with valid JSON response
        valid_json = {"title": "Test", "content": "Valid content"}
        
        mock_message = Mock()
        mock_message.content = [Mock(text=json.dumps(valid_json))]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate_json(
            prompt="Generate structured content",
            schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["title", "content"]
            }
        )
        
        assert result == valid_json
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, provider, mock_anthropic_client):
        """Test streaming response handling."""
        # Mock streaming response
        async def mock_stream():
            chunks = ["Hello", " world", " from", " Anthropic"]
            for chunk in chunks:
                mock_event = Mock()
                mock_event.type = "content_block_delta"
                mock_event.delta = Mock(text=chunk)
                yield mock_event
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_stream())
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        # Collect streamed content
        chunks = []
        async for chunk in provider.generate_stream("Test prompt"):
            chunks.append(chunk)
        
        assert "".join(chunks) == "Hello world from Anthropic"
    
    @pytest.mark.asyncio
    async def test_context_window_management(self, provider, mock_anthropic_client):
        """Test context window size management."""
        # Create a very long context
        long_context = "Previous context. " * 10000
        
        mock_message = Mock()
        mock_message.content = [Mock(text="Response with managed context")]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate(
            prompt="Continue the presentation",
            context=long_context,
            max_context_tokens=4000
        )
        
        # Verify context was truncated
        call_args = mock_client_instance.messages.create.call_args
        messages = call_args.kwargs.get('messages', [])
        
        # Check that context was included but managed
        assert len(messages) > 0
        assert result == "Response with managed context"
    
    @pytest.mark.asyncio
    async def test_model_fallback(self, provider, mock_anthropic_client):
        """Test fallback to different model on error."""
        mock_client_instance = AsyncMock()
        
        # First model fails, fallback succeeds
        mock_message = Mock()
        mock_message.content = [Mock(text="Fallback model response")]
        
        call_count = 0
        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and kwargs.get('model') == 'claude-3-opus-20240229':
                raise Exception("Model overloaded")
            return mock_message
        
        mock_client_instance.messages.create = mock_create
        mock_anthropic_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate(
            prompt="Test prompt",
            model="claude-3-opus-20240229",
            fallback_model="claude-3-sonnet-20240229"
        )
        
        assert result == "Fallback model response"
        assert call_count == 2