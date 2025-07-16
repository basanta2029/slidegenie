import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import numpy as np
from utils.enhanced_content_analyzer import EnhancedContentAnalyzer

# Initialize enhanced analyzer
enhanced_analyzer = EnhancedContentAnalyzer()

def clean_text(text):
    """Clean and normalize text for analysis"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?]', ' ', text)
    return text.lower()

def extract_keywords(text, top_n=20):
    """Extract key terms from text using TF-IDF"""
    if not text or len(text.strip()) < 10:
        return []
    
    try:
        # Use TF-IDF to find important terms
        vectorizer = TfidfVectorizer(
            max_features=top_n,
            stop_words='english',
            ngram_range=(1, 2),  # Include bigrams
            min_df=1,
            max_df=0.95
        )
        
        # Fit and transform the text
        tfidf_matrix = vectorizer.fit_transform([clean_text(text)])
        feature_names = vectorizer.get_feature_names_out()
        
        # Get scores for each term
        scores = tfidf_matrix.toarray()[0]
        
        # Create keyword-score pairs and sort by score
        keywords = [(feature_names[i], scores[i]) for i in range(len(feature_names)) if scores[i] > 0]
        keywords.sort(key=lambda x: x[1], reverse=True)
        
        return [kw[0] for kw in keywords[:top_n]]
    
    except Exception as e:
        st.warning(f"Keyword extraction failed: {str(e)}")
        return []

def calculate_similarity(user_goals, extracted_content):
    """Calculate similarity between user goals and extracted content"""
    if not user_goals or not extracted_content:
        return 0.0, [], "No content to analyze"
    
    try:
        # Clean both texts
        clean_goals = clean_text(user_goals)
        clean_content = clean_text(extracted_content)
        
        if len(clean_goals) < 5 or len(clean_content) < 5:
            return 0.0, [], "Insufficient content for analysis"
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        
        # Fit on both texts
        tfidf_matrix = vectorizer.fit_transform([clean_goals, clean_content])
        
        # Calculate cosine similarity
        similarity_matrix = cosine_similarity(tfidf_matrix)
        similarity_score = similarity_matrix[0][1]  # Similarity between first and second document
        
        # Extract common keywords
        feature_names = vectorizer.get_feature_names_out()
        goals_vector = tfidf_matrix[0].toarray()[0]
        content_vector = tfidf_matrix[1].toarray()[0]
        
        # Find terms that appear in both with significant weight
        common_keywords = []
        for i, term in enumerate(feature_names):
            if goals_vector[i] > 0.1 and content_vector[i] > 0.1:
                avg_weight = (goals_vector[i] + content_vector[i]) / 2
                common_keywords.append((term, avg_weight))
        
        # Sort by weight and take top terms
        common_keywords.sort(key=lambda x: x[1], reverse=True)
        top_common = [kw[0] for kw in common_keywords[:10]]
        
        # Generate analysis message
        if similarity_score > 0.7:
            analysis = "<Excellent match! Your uploaded content strongly aligns with your goals."
        elif similarity_score > 0.5:
            analysis = "Good alignment between your goals and uploaded content."
        elif similarity_score > 0.3:
            analysis = "Moderate relevance. Consider adding more specific content."
        else:
            analysis = "Low relevance detected. Upload content might not match your goals."
        
        return float(similarity_score), top_common, analysis
    
    except Exception as e:
        return 0.0, [], f"Analysis error: {str(e)}"

def generate_context_prompt(user_goals, extracted_content, similarity_score, common_keywords):
    """Generate enhanced context for AI based on similarity analysis"""
    
    context_parts = []
    
    # Add user goals
    context_parts.append(f"USER OBJECTIVES: {user_goals}")
    
    # Add similarity insights
    if similarity_score > 0.5:
        context_parts.append(f"CONTENT RELEVANCE: High relevance detected (similarity: {similarity_score:.2f})")
        if common_keywords:
            context_parts.append(f"KEY THEMES: {', '.join(common_keywords[:5])}")
    else:
        context_parts.append(f"CONTENT RELEVANCE: Lower relevance (similarity: {similarity_score:.2f}) - focus on user goals")
    
    # Add supporting content
    if extracted_content:
        # Truncate if too long
        if len(extracted_content) > 2000:
            truncated_content = extracted_content[:2000] + "..."
            context_parts.append(f"SUPPORTING MATERIALS (truncated): {truncated_content}")
        else:
            context_parts.append(f"SUPPORTING MATERIALS: {extracted_content}")
    
    return "\n\n".join(context_parts)

def analyze_content_relevance(user_goals, uploaded_files_content):
    """Main function to analyze and display content relevance"""
    
    if not user_goals:
        return None, "Please enter your presentation goals first."
    
    if not uploaded_files_content:
        return None, "No uploaded content to analyze."
    
    # Calculate similarity
    similarity_score, common_keywords, analysis_message = calculate_similarity(
        user_goals, uploaded_files_content
    )
    
    # Display analysis results
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**Content Relevance Analysis:** {analysis_message}")
        
        if common_keywords:
            st.markdown(f"**Key themes detected:** {', '.join(common_keywords[:5])}")
    
    with col2:
        # Visual indicator
        if similarity_score > 0.7:
            st.success(f"Match: {similarity_score:.1%}")
        elif similarity_score > 0.5:
            st.info(f"Match: {similarity_score:.1%}")
        elif similarity_score > 0.3:
            st.warning(f"Match: {similarity_score:.1%}")
        else:
            st.error(f"Match: {similarity_score:.1%}")
    
    # Generate enhanced context for AI
    enhanced_context = generate_context_prompt(
        user_goals, uploaded_files_content, similarity_score, common_keywords
    )
    
    return enhanced_context, analysis_message 

def analyze_image_slide_similarity(slides_data, slide_images):
    """
    Analyze similarity between slide content and available images using AI Vision
    Full AI vision analysis - no limited features
    """
    if not slides_data or not slide_images:
        return slides_data
    
    try:
        # Use AI Vision for intelligent image-to-slide matching
        st.info("Using AI Vision for intelligent image-to-slide matching...")
        return enhanced_analyzer.enhanced_image_slide_matching(slides_data, slide_images)
    except Exception as e:
        st.error(f"AI vision analysis failed: {str(e)}")
        st.info("Falling back to basic filename matching...")
        return _fallback_image_slide_similarity(slides_data, slide_images)

def _fallback_image_slide_similarity(slides_data, slide_images):
    """
    Fallback image-to-slide matching using TF-IDF similarity
    """
    slides = slides_data.get('slides', [])
    
    for slide in slides:
        slide_content = ""
        
        # Combine slide title and content for analysis
        slide_title = slide.get('title', '')
        slide_content += slide_title + " "
        
        content_items = slide.get('content', [])
        if isinstance(content_items, list):
            slide_content += " ".join(str(item) for item in content_items)
        else:
            slide_content += str(content_items)
        
        # Clean slide content
        clean_slide_content = clean_text(slide_content)
        
        # Find best matching image
        best_image = None
        best_score = 0.0
        
        for image_info in slide_images:
            image_name = image_info['name']
            
            # Extract keywords from image filename
            image_keywords = extract_image_keywords(image_name)
            
            # Calculate similarity between slide content and image keywords
            if image_keywords and clean_slide_content:
                try:
                    # Create combined text for image context
                    image_context = " ".join(image_keywords)
                    
                    # Use TF-IDF similarity
                    vectorizer = TfidfVectorizer(
                        stop_words='english',
                        ngram_range=(1, 2),
                        min_df=1,
                        max_df=0.95
                    )
                    
                    # Combine slide content and image context
                    texts = [clean_slide_content, image_context]
                    tfidf_matrix = vectorizer.fit_transform(texts)
                    
                    # Calculate similarity
                    similarity_matrix = cosine_similarity(tfidf_matrix)
                    similarity_score = similarity_matrix[0][1]
                    
                    # Check for direct keyword matches (boost score)
                    slide_words = set(clean_slide_content.lower().split())
                    image_words = set(word.lower() for word in image_keywords)
                    common_words = slide_words.intersection(image_words)
                    
                    # Boost score for direct matches
                    if common_words:
                        keyword_boost = len(common_words) * 0.3
                        similarity_score += keyword_boost
                    
                    # Update best match if this is better
                    if similarity_score > best_score and similarity_score > 0.3:  # Higher threshold
                        best_score = similarity_score
                        best_image = image_name
                        
                except Exception:
                    continue
        
        # Add suggested image to slide if found
        if best_image and best_score > 0.3:  # Higher threshold
            slide['suggested_image'] = best_image
            slide['image_similarity_score'] = round(best_score, 3)
    
    return slides_data

def extract_image_keywords(filename):
    """
    Extract meaningful keywords from image filename
    """
    # Remove file extension
    name_without_ext = filename.rsplit('.', 1)[0]
    
    # Replace common separators with spaces
    clean_name = name_without_ext.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    
    # Split into words
    words = clean_name.split()
    
    # Filter out common non-descriptive words
    stop_words = {'screenshot', 'image', 'photo', 'pic', 'img', 'figure', 'fig', 'chart', 'graph', 'plot', 'data', '2024', '2025', 'png', 'jpg', 'jpeg'}
    
    # Keep meaningful words (length > 2, not in stop words)
    keywords = [word for word in words if len(word) > 2 and word.lower() not in stop_words]
    
    return keywords

def calculate_content_image_relevance(user_goals, slide_images):
    """
    Calculate how relevant uploaded images are to user goals using AI Vision
    """
    if not user_goals or not slide_images:
        return []
    
    try:
        # Use AI Vision for enhanced relevance calculation
        st.info("Using AI Vision to analyze image relevance...")
        return enhanced_analyzer.calculate_enhanced_content_relevance(user_goals, slide_images)
    except Exception as e:
        st.warning(f"AI vision relevance analysis failed: {str(e)}")
        return _fallback_content_image_relevance(user_goals, slide_images)

def _fallback_content_image_relevance(user_goals, slide_images):
    """
    Fallback content-image relevance calculation using filename analysis
    """
    relevance_scores = []
    clean_goals = clean_text(user_goals)
    
    for image_info in slide_images:
        image_name = image_info['name']
        image_keywords = extract_image_keywords(image_name)
        
        if image_keywords:
            try:
                # Create image context from keywords
                image_context = " ".join(image_keywords)
                
                # Calculate similarity with user goals
                vectorizer = TfidfVectorizer(
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=1
                )
                
                texts = [clean_goals, image_context]
                tfidf_matrix = vectorizer.fit_transform(texts)
                similarity_matrix = cosine_similarity(tfidf_matrix)
                similarity_score = similarity_matrix[0][1]
                
                # Check for direct keyword matches
                goal_words = set(clean_goals.lower().split())
                image_words = set(word.lower() for word in image_keywords)
                common_words = goal_words.intersection(image_words)
                
                if common_words:
                    similarity_score += len(common_words) * 0.2
                
                relevance_scores.append({
                    'image_name': image_name,
                    'similarity_score': round(similarity_score, 3),
                    'keywords': image_keywords,
                    'common_themes': list(common_words) if common_words else []
                })
                
            except Exception:
                relevance_scores.append({
                    'image_name': image_name,
                    'similarity_score': 0.0,
                    'keywords': image_keywords,
                    'common_themes': []
                })
    
    # Sort by similarity score
    relevance_scores.sort(key=lambda x: x['similarity_score'], reverse=True)
    return relevance_scores