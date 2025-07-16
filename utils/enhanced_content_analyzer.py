import streamlit as st
import base64
import io
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import openai
import config
import re
from typing import Optional

class EnhancedContentAnalyzer:
    def __init__(self):
        self._openai_client: Optional[openai.OpenAI] = None
        self._sentence_model = None
        self._sentence_transformer = None
    
    @property
    def openai_client(self):
        if self._openai_client is None:
            try:
                self._openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception as e:
                st.warning(f"Could not initialize OpenAI client: {str(e)}")
        return self._openai_client
    
    @property
    def sentence_model(self):
        if self._sentence_model is None:
            try:
                # Import here to avoid startup issues
                from sentence_transformers import SentenceTransformer
                self._sentence_transformer = SentenceTransformer
                self._sentence_model = self._sentence_transformer('all-MiniLM-L6-v2')
            except Exception as e:
                st.warning(f"Could not load sentence transformer model: {str(e)}")
        return self._sentence_model
    
    def analyze_image_content(self, image_bytes, image_name):
        """
        Analyze image content using OpenAI Vision API (full AI vision - no fallback)
        """
        if not self.openai_client:
            raise Exception("OpenAI client not available for AI vision analysis")
            
        try:
            # Convert image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Use OpenAI Vision API with detailed analysis
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image in detail for presentation use. Provide: 1) Main subject/topic and scientific/technical elements, 2) Key visual elements and data shown, 3) Relevant keywords for content matching, 4) Potential slide context (intro, methods, results, conclusion), 5) Technical terms and concepts visible. Be specific and technical when appropriate."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=400  # Increased for more detailed analysis
            )
            
            analysis = response.choices[0].message.content
            st.success(f"🔍 AI Vision analyzed: {image_name}")
            return analysis
            
        except Exception as e:
            # Fallback to filename analysis if Vision API fails
            st.warning(f"AI vision analysis failed for {image_name}: {str(e)}")
            return self._analyze_filename(image_name)
    
    def _analyze_filename(self, filename):
        """
        Fallback filename-based analysis
        """
        name_without_ext = filename.rsplit('.', 1)[0]
        clean_name = name_without_ext.replace('_', ' ').replace('-', ' ').replace('.', ' ')
        return f"Image related to: {clean_name}"
    
    def calculate_semantic_similarity(self, text1, text2):
        """
        Calculate semantic similarity using sentence transformers
        """
        if not self.sentence_model:
            # Fallback to basic text similarity
            return self._calculate_basic_similarity(text1, text2)
        
        try:
            embeddings = self.sentence_model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            st.warning(f"Semantic similarity calculation failed: {str(e)}")
            return self._calculate_basic_similarity(text1, text2)
    
    def _calculate_basic_similarity(self, text1, text2):
        """
        Basic similarity calculation as fallback
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0
    
    def analyze_slide_context(self, slide_content, slide_position, total_slides):
        """
        Analyze slide context for context-aware boosting
        """
        position_weight = 1.0
        
        # Opening slides (first 20%) get higher weight for introductory images
        if slide_position <= total_slides * 0.2:
            position_weight = 1.3
            context_keywords = ["introduction", "overview", "background", "welcome", "agenda"]
        
        # Middle slides (20-80%) get normal weight for content images
        elif slide_position <= total_slides * 0.8:
            position_weight = 1.0
            context_keywords = ["data", "results", "analysis", "findings", "methodology"]
        
        # Closing slides (last 20%) get higher weight for conclusion images
        else:
            position_weight = 1.2
            context_keywords = ["conclusion", "summary", "future", "recommendations", "thanks"]
        
        # Check if slide content matches expected context
        slide_text = slide_content.lower()
        context_match = any(keyword in slide_text for keyword in context_keywords)
        
        if context_match:
            position_weight *= 1.1
        
        return position_weight, context_keywords
    
    def enhanced_image_slide_matching(self, slides_data, slide_images):
        """
        Enhanced image-to-slide matching using AI vision and semantic similarity
        """
        if not slides_data or not slide_images:
            return slides_data
        
        slides = slides_data.get('slides', [])
        total_slides = len(slides)
        
        # First, analyze all images with AI vision
        image_analyses = {}
        for image_info in slide_images:
            image_name = image_info['name']
            image_bytes = image_info['bytes']
            
            # Analyze image content
            image_description = self.analyze_image_content(image_bytes, image_name)
            image_analyses[image_name] = image_description
        
        # Match images to slides
        for i, slide in enumerate(slides):
            slide_position = i + 1
            slide_content = self._combine_slide_content(slide)
            
            # Get context-aware boosting
            position_weight, context_keywords = self.analyze_slide_context(
                slide_content, slide_position, total_slides
            )
            
            best_image = None
            best_score = 0.0
            
            # Compare with each image
            for image_name, image_description in image_analyses.items():
                # Calculate semantic similarity
                semantic_score = self.calculate_semantic_similarity(
                    slide_content, image_description
                )
                
                # Apply context-aware boosting
                boosted_score = semantic_score * position_weight
                
                # Additional keyword matching bonus
                slide_words = set(slide_content.lower().split())
                image_words = set(image_description.lower().split())
                common_words = slide_words.intersection(image_words)
                
                if common_words:
                    keyword_bonus = min(len(common_words) * 0.1, 0.3)  # Max 30% bonus
                    boosted_score += keyword_bonus
                
                # Check for context keyword matches
                context_match = any(keyword in image_description.lower() for keyword in context_keywords)
                if context_match:
                    boosted_score += 0.1
                
                # Update best match if this is better and meets threshold
                if boosted_score > best_score and boosted_score > 0.4:  # Higher threshold for better matches
                    best_score = boosted_score
                    best_image = image_name
            
            # Add suggested image to slide if found
            if best_image and best_score > 0.4:
                slide['suggested_image'] = best_image
                slide['image_similarity_score'] = round(best_score, 3)
                slide['image_description'] = image_analyses[best_image]
        
        return slides_data
    
    def _combine_slide_content(self, slide):
        """
        Combine slide title and content into a single text for analysis
        """
        slide_content = slide.get('title', '') + " "
        content_items = slide.get('content', [])
        
        if isinstance(content_items, list):
            slide_content += " ".join(str(item) for item in content_items)
        else:
            slide_content += str(content_items)
        
        return slide_content.strip()
    
    def calculate_enhanced_content_relevance(self, user_goals, slide_images):
        """
        Calculate enhanced content relevance using AI vision and semantic similarity
        """
        if not user_goals or not slide_images:
            return []
        
        relevance_scores = []
        
        for image_info in slide_images:
            image_name = image_info['name']
            image_bytes = image_info['bytes']
            
            # Analyze image content with AI
            image_description = self.analyze_image_content(image_bytes, image_name)
            
            # Calculate semantic similarity
            similarity_score = self.calculate_semantic_similarity(user_goals, image_description)
            
            # Extract key themes from image description
            image_themes = self._extract_themes(image_description)
            goal_themes = self._extract_themes(user_goals)
            common_themes = set(image_themes).intersection(set(goal_themes))
            
            relevance_scores.append({
                'image_name': image_name,
                'similarity_score': round(similarity_score, 3),
                'image_description': image_description,
                'keywords': image_themes,
                'common_themes': list(common_themes)
            })
        
        # Sort by similarity score
        relevance_scores.sort(key=lambda x: x['similarity_score'], reverse=True)
        return relevance_scores
    
    def _extract_themes(self, text):
        """
        Extract key themes from text using simple keyword extraction
        """
        # Remove common words and extract meaningful terms
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Return top frequent words
        from collections import Counter
        word_counts = Counter(meaningful_words)
        return [word for word, count in word_counts.most_common(10)]

# Global instance
enhanced_analyzer = EnhancedContentAnalyzer()