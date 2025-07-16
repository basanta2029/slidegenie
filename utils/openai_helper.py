# utils/openai_helper.py
import openai
import config
import json

def generate_presentation_content(content, slide_count, pres_type, input_type, slide_images=None):
    """
    Generate presentation content using OpenAI API (v1.0+) with image support
    """
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Add image context if available
        image_context = ""
        if slide_images and len(slide_images) > 0:
            image_names = [img['name'] for img in slide_images]
            image_context = f"""
        
        AVAILABLE IMAGES FOR SLIDES: {', '.join(image_names)}
        Instructions for image placement:
        - Strategically suggest which slides should include images
        - Match image content to slide topics when possible
        - Include "suggested_image" field for relevant slides
        - Images available: {len(slide_images)} total images
        """
        
        # Create the prompt based on input type and presentation type
        prompt = f"""
        Create a comprehensive {slide_count}-slide presentation for a {pres_type} based on the following {input_type.lower()}:

        Content: {content}
        {image_context}

        Requirements for HUMANIZED and ENGAGING content:
        1. Write in a conversational, approachable tone while maintaining professionalism
        2. Use storytelling elements - set scenes, create narratives, and connect with the audience
        3. Include relatable analogies, real-world examples, and practical scenarios
        4. Add emotional context - why should the audience care? What's the human impact?
        5. Use inclusive language and make complex concepts accessible
        6. Include thought-provoking questions and interactive elements
        7. Provide rich context with background stories, current relevance, and future implications
        8. Make each bullet point a complete, engaging thought that flows naturally

        Content Style Guidelines:
        - Start with compelling hooks and attention-grabbers
        - Use "you" and "we" to engage the audience directly
        - Include specific numbers, dates, and concrete examples when possible
        - Add surprising facts, interesting quotes, or compelling statistics
        - Connect abstract concepts to everyday experiences
        - Show both challenges and opportunities
        - Include calls to action and next steps

        Structure the presentation with:
        - Compelling title that sparks curiosity
        - Opening hook that connects with the audience
        - Story-driven content with clear progression
        - Rich context and detailed explanations
        - Practical takeaways and actionable insights
        - Memorable conclusion with lasting impact

        Return the response as a JSON object with this structure:
        {{
            "title": "Compelling, Human-Centered Title",
            "slides": [
                {{
                    "number": 1,
                    "title": "Engaging Slide Title",
                    "content": [
                        "Conversational, story-driven point that connects with audience experience and provides rich context",
                        "Engaging explanation with real-world examples, analogies, and emotional resonance that makes complex ideas accessible", 
                        "Action-oriented insight with practical implications, surprising facts, and clear relevance to audience needs"
                    ],
                    "notes": "Rich speaker notes with storytelling cues, audience engagement tips, personal anecdotes, transition suggestions, and additional context that helps the presenter connect authentically with the audience",
                    "suggested_image": "image_filename.jpg (if relevant image available)"
                }}
            ]
        }}

        Make the content feel like a compelling conversation between experts and curious minds. Focus on human stories, practical impact, and emotional connection while maintaining {pres_type} standards.
        """

        # Choose model based on complexity (slide count)
        model = "gpt-4" if slide_count > 15 else "gpt-3.5-turbo"
        max_tokens = 4000 if model == "gpt-3.5-turbo" else 8000
        
        # Make API call using new format with increased token limit
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert presentation designer specializing in academic and research presentations. Always respond with valid JSON. Ensure the response is complete and not truncated."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )

        # Extract and parse the response
        content_text = response.choices[0].message.content
        
        # Debug: Show content length and check for truncation
        if len(content_text) > 3900:  # Close to max tokens
            print(f"Warning: Response may be truncated. Length: {len(content_text)}")
        
        # Try to parse JSON response
        try:
            result = json.loads(content_text)
            
            # Validate the result structure
            if not isinstance(result, dict) or 'slides' not in result:
                raise ValueError("Invalid response structure")
            
            # Ensure we have the expected number of slides
            if len(result.get('slides', [])) < slide_count:
                print(f"Warning: Only {len(result.get('slides', []))} slides generated instead of {slide_count}")
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Raw content: {content_text[:500]}...")  # Show first 500 chars for debugging
            
            # Try to extract partial content if JSON is incomplete
            partial_result = _extract_partial_content(content_text, slide_count, pres_type)
            if partial_result:
                return partial_result
            
            # If all else fails, create a simple structure
            return {
                "title": f"{pres_type} Presentation",
                "slides": [
                    {
                        "number": 1,
                        "title": "Generated Content",
                        "content": [content[:200] + "..." if len(content) > 200 else content],
                        "notes": "This is a generated slide from your content."
                    }
                ]
            }

    except Exception as e:
        raise Exception(f"Error generating content: {str(e)}")

def _extract_partial_content(content_text, slide_count, pres_type):
    """
    Try to extract partial content from truncated response
    """
    try:
        # Look for JSON-like structure in the text
        import re
        
        # Try to find title
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', content_text)
        title = title_match.group(1) if title_match else f"{pres_type} Presentation"
        
        # Try to find slides array
        slides_match = re.search(r'"slides"\s*:\s*\[(.+)', content_text, re.DOTALL)
        if not slides_match:
            return None
        
        slides_text = slides_match.group(1)
        
        # Try to extract individual slides
        slides = []
        slide_matches = re.finditer(r'\{[^}]*"number"\s*:\s*(\d+)[^}]*"title"\s*:\s*"([^"]+)"[^}]*\}', slides_text, re.DOTALL)
        
        for match in slide_matches:
            slide_number = int(match.group(1))
            slide_title = match.group(2)
            
            # Extract content if possible
            slide_content = ["Content extracted from partial response"]
            
            slides.append({
                "number": slide_number,
                "title": slide_title,
                "content": slide_content,
                "notes": "Partially extracted content"
            })
            
            if len(slides) >= slide_count:
                break
        
        if slides:
            return {
                "title": title,
                "slides": slides
            }
        
    except Exception:
        pass
    
    return None