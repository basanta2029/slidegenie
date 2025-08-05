"""Unit tests for OpenAI provider."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from typing import Dict, Any

from app.services.ai.openai_provider import OpenAIProvider
from tests.unit.utils.test_helpers import MockResponse


class TestOpenAIProvider:
    """Test suite for OpenAI provider."""
    
    @pytest.fixture
    def provider(self):
        """Create OpenAI provider instance."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-api-key'}):
            return OpenAIProvider()
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        with patch('openai.AsyncOpenAI') as mock_client:
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_generate_successful_response(self, provider, mock_openai_client):
        """Test successful content generation."""
        # Mock response
        mock_choice = Mock()
        mock_choice.message = Mock(content="Generated presentation content")
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_client.return_value = mock_client_instance
        
        # Reinitialize provider to use mocked client
        provider._client = None
        
        # Test generation
        result = await provider.generate(
            prompt="Create a presentation about machine learning",
            max_tokens=1000,
            temperature=0.8
        )
        
        assert result == "Generated presentation content"
        mock_client_instance.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_with_function_calling(self, provider, mock_openai_client):
        """Test generation with function calling."""
        # Mock function call response
        function_response = {
            "name": "create_presentation_outline",
            "arguments": json.dumps({
                "title": "Machine Learning Basics",
                "sections": ["Introduction", "Algorithms", "Applications", "Future"]
            })
        }
        
        mock_choice = Mock()
        mock_choice.message = Mock(
            content=None,
            function_call=Mock(**function_response)
        )
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = Mock(prompt_tokens=150, completion_tokens=100, total_tokens=250)
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        # Test with functions
        functions = [{
            "name": "create_presentation_outline",
            "description": "Create a presentation outline",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "sections": {"type": "array", "items": {"type": "string"}}
                }
            }
        }]
        
        result = await provider.generate_with_functions(
            prompt="Create presentation outline",
            functions=functions
        )
        
        assert result["name"] == "create_presentation_outline"
        assert "title" in json.loads(result["arguments"])
    
    @pytest.mark.asyncio
    async def test_generate_json_response(self, provider, mock_openai_client):
        """Test JSON response generation with response format."""
        json_content = {
            "title": "Deep Learning Fundamentals",
            "duration": 45,
            "slides": 20
        }
        
        mock_choice = Mock()
        mock_choice.message = Mock(content=json.dumps(json_content))
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = Mock(prompt_tokens=80, completion_tokens=40, total_tokens=120)
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate_json(
            prompt="Create presentation metadata",
            response_format={"type": "json_object"}
        )
        
        assert result == json_content
        
        # Verify response_format was passed
        call_args = mock_client_instance.chat.completions.create.call_args
        assert call_args.kwargs.get('response_format') == {"type": "json_object"}
    
    @pytest.mark.asyncio
    async def test_generate_with_gpt4_vision(self, provider, mock_openai_client):
        """Test GPT-4 Vision capabilities."""
        mock_choice = Mock()
        mock_choice.message = Mock(content="Analysis of the uploaded diagram shows...")
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = Mock(prompt_tokens=200, completion_tokens=100, total_tokens=300)
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        # Test with image
        result = await provider.generate_with_vision(
            prompt="Analyze this diagram and create slides",
            image_url="https://example.com/diagram.png",
            model="gpt-4-vision-preview"
        )
        
        assert "Analysis of the uploaded diagram" in result
        
        # Verify image was included in messages
        call_args = mock_client_instance.chat.completions.create.call_args
        messages = call_args.kwargs.get('messages', [])
        assert any("image_url" in str(msg) for msg in messages)
    
    @pytest.mark.asyncio
    async def test_embeddings_generation(self, provider, mock_openai_client):
        """Test text embeddings generation."""
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 256  # 1280 dimensions
        
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=mock_embedding)]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_embedding_response)
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        # Test embedding generation
        result = await provider.generate_embedding(
            text="Sample presentation content for embedding",
            model="text-embedding-3-small"
        )
        
        assert result == mock_embedding
        assert len(result) == 1280
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, provider, mock_openai_client):
        """Test streaming response handling."""
        # Mock streaming chunks
        async def mock_stream():
            chunks = [
                Mock(choices=[Mock(delta=Mock(content="Streaming"))]),
                Mock(choices=[Mock(delta=Mock(content=" presentation"))]),
                Mock(choices=[Mock(delta=Mock(content=" content"))]),
                Mock(choices=[Mock(delta=Mock(content=None))])  # End chunk
            ]
            for chunk in chunks:
                yield chunk
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        # Collect streamed content
        chunks = []
        async for chunk in provider.generate_stream("Test prompt", stream=True):
            if chunk:
                chunks.append(chunk)
        
        assert "".join(chunks) == "Streaming presentation content"
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, provider, mock_openai_client):
        """Test retry mechanism on rate limit errors."""
        mock_client_instance = AsyncMock()
        
        # First call raises rate limit error, second succeeds
        mock_choice = Mock()
        mock_choice.message = Mock(content="Success after retry")
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = Mock(prompt_tokens=50, completion_tokens=25, total_tokens=75)
        
        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("Rate limit exceeded"),
                mock_completion
            ]
        )
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await provider.generate("Test prompt")
        
        assert result == "Success after retry"
        assert mock_client_instance.chat.completions.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_calculate_cost(self, provider):
        """Test cost calculation for different models."""
        # Test GPT-4 cost
        gpt4_cost = provider.calculate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="gpt-4"
        )
        
        # Test GPT-3.5 cost
        gpt35_cost = provider.calculate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="gpt-3.5-turbo"
        )
        
        # GPT-4 should be more expensive
        assert gpt4_cost > gpt35_cost
        assert gpt4_cost > 0
        assert gpt35_cost > 0
    
    @pytest.mark.asyncio
    async def test_model_selection_based_on_task(self, provider, mock_openai_client):
        """Test automatic model selection based on task complexity."""
        # Simple task uses GPT-3.5
        mock_choice = Mock()
        mock_choice.message = Mock(content="Simple response")
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = Mock(prompt_tokens=30, completion_tokens=20, total_tokens=50)
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_client.return_value = mock_client_instance
        
        provider._client = None
        
        result = await provider.generate(
            prompt="Create a simple title slide",
            auto_select_model=True,
            task_complexity="simple"
        )
        
        # Verify GPT-3.5 was used
        call_args = mock_client_instance.chat.completions.create.call_args
        assert "gpt-3.5" in call_args.kwargs.get('model', '')
    
    @pytest.mark.asyncio
    async def test_token_counting(self, provider):
        """Test token counting functionality."""
        text = "This is a sample text for counting tokens in a presentation."
        
        # Test token counting
        token_count = provider.count_tokens(text, model="gpt-3.5-turbo")
        
        assert token_count > 0
        assert isinstance(token_count, int)
        
        # Longer text should have more tokens
        long_text = text * 10
        long_token_count = provider.count_tokens(long_text, model="gpt-3.5-turbo")
        
        assert long_token_count > token_count