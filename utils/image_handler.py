import streamlit as st
from PIL import Image
import io
import base64
import os

def process_slide_images(uploaded_images):
    """Process images that will be embedded in slides"""
    processed_images = []
    
    if not uploaded_images:
        return processed_images
    
    for img_file in uploaded_images:
        try:
            # Open and process the image
            image = Image.open(img_file)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Resize for slide use (max 800px width to keep file size reasonable)
            max_width = 800
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save to bytes buffer
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG', quality=85)
            img_bytes = img_buffer.getvalue()
            
            # Create image info
            image_info = {
                'name': img_file.name,
                'bytes': img_bytes,
                'width': image.width,
                'height': image.height,
                'size_kb': len(img_bytes) // 1024
            }
            
            processed_images.append(image_info)
            
        except Exception as e:
            st.error(f"Error processing image {img_file.name}: {str(e)}")
    
    return processed_images

def create_image_base64(image_bytes):
    """Convert image bytes to base64 for embedding"""
    return base64.b64encode(image_bytes).decode()

def display_image_preview(processed_images):
    """Display preview of uploaded images"""
    if not processed_images:
        return
    
    st.markdown("### 🖼️ Images for Slides")
    
    cols = st.columns(min(len(processed_images), 3))
    
    for i, img_info in enumerate(processed_images):
        with cols[i % 3]:
            # Display image
            image = Image.open(io.BytesIO(img_info['bytes']))
            st.image(image, caption=img_info['name'], use_container_width=True)
            
            # Show info
            st.caption(f"Size: {img_info['size_kb']}KB • {img_info['width']}×{img_info['height']}")

def validate_slide_images(uploaded_images):
    """Validate images for slide use"""
    if not uploaded_images:
        return []
    
    valid_images = []
    max_size = 5 * 1024 * 1024  # 5MB
    supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    
    for img in uploaded_images:
        # Check file size
        if img.size > max_size:
            st.error(f"❌ Image '{img.name}' is too large (max 5MB)")
            continue
        
        # Check format
        file_extension = img.name.split('.')[-1].lower()
        if file_extension not in supported_formats:
            st.error(f"❌ Image '{img.name}' format not supported")
            continue
        
        valid_images.append(img)
    
    return valid_images

def suggest_image_placement(user_goals, image_names):
    """Suggest which slides should include images based on content"""
    suggestions = []
    
    # Simple keyword matching for image placement
    goal_words = user_goals.lower().split()
    
    for img_name in image_names:
        img_keywords = img_name.lower().replace('_', ' ').replace('-', ' ').split('.')
        
        # Look for matches between image filename and goals
        matches = []
        for word in goal_words:
            for keyword in img_keywords:
                if len(word) > 3 and word in keyword:
                    matches.append(word)
        
        if matches:
            suggestions.append({
                'image': img_name,
                'suggested_slides': ['Introduction', 'Main Content'],
                'reason': f"Keywords found: {', '.join(set(matches))}"
            })
        else:
            suggestions.append({
                'image': img_name,
                'suggested_slides': ['Supporting Content'],
                'reason': "General supporting material"
            })
    
    return suggestions 