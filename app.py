# app.py
import streamlit as st
from datetime import datetime
import config
from utils.openai_helper import generate_presentation_content
from utils.pptx_generator import create_presentation, create_pptx_buffer
from utils.pdf_generator import create_pdf_from_slides
from utils.file_processor import process_uploaded_files, validate_file_upload, check_tesseract_config
from utils.content_analyzer import analyze_content_relevance, analyze_image_slide_similarity, calculate_content_image_relevance
from utils.image_handler import process_slide_images, validate_slide_images, display_image_preview

# Page config
st.set_page_config(
    page_title="SlideGenie - Research to Slides",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stButton > button {
        background-color: #2E7D32;
        color: white;
    }
    .stButton > button:hover {
        background-color: #1B5E20;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🎯 SlideGenie for Researchers")
st.markdown("Transform your research into presentations in seconds!")

# Initialize session state
if 'generated_slides' not in st.session_state:
    st.session_state.generated_slides = None

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key handling
    if config.OPENAI_API_KEY:
        st.success("✅ API Key loaded from .env")
    else:
        api_key = st.text_input("OpenAI API Key", type="password")
        if api_key:
            config.OPENAI_API_KEY = api_key
            st.success("✅ API Key configured!")
    
    st.markdown("---")
    st.markdown("### About")
    st.info("SlideGenie v0.1.0\nBuilt for researchers, by researchers")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎯 Your Presentation Goals")
    
    # Main content input - user goals and objectives
    user_goals = st.text_area(
        "What do you want to achieve with this presentation?",
        height=150,
        placeholder="Example: I want to present my climate change research findings to convince stakeholders to fund marine conservation efforts. The presentation should emphasize urgent action needed and include compelling data about coral reef degradation...",
        help="Describe your objectives, target audience, key messages, and desired outcomes"
    )
    
    st.markdown("---")
    
    # Supporting Materials Section
    st.subheader("📚 Supporting Materials")
    st.markdown("Upload documents and images to provide context and enhance your presentation")
    
    # Create tabs for different upload types
    tab1, tab2 = st.tabs(["📄 Documents", "🖼️ Slide Images"])
    
    with tab1:
        st.markdown("**Upload PDFs or images containing research content, data, or supporting text**")
        
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp'],
            accept_multiple_files=True,
            help="Upload research papers, reports, screenshots, or any documents with relevant content",
            key="supporting_files"
        )
        
        extracted_content = ""
        if uploaded_files:
            valid_files = validate_file_upload(uploaded_files)
            if valid_files:
                # Check OCR availability for images
                has_images = any(f.type.startswith("image/") for f in valid_files)
                if has_images and not check_tesseract_config():
                    st.warning("⚠️ OCR not available for image files. Only PDFs will be processed.")
                    valid_files = [f for f in valid_files if f.type == "application/pdf"]
                
                if valid_files:
                    with st.spinner("📖 Extracting content from uploaded files..."):
                        extracted_content = process_uploaded_files(valid_files)
                        if extracted_content:
                            st.success(f"✅ Successfully processed {len(valid_files)} file(s)")
                            
                            # Show content relevance analysis
                            if user_goals and extracted_content:
                                st.markdown("#### 🔍 Content Relevance Analysis")
                                enhanced_context, analysis_msg = analyze_content_relevance(user_goals, extracted_content)
                                
                                # Store enhanced context for AI generation
                                if 'enhanced_context' not in st.session_state:
                                    st.session_state.enhanced_context = enhanced_context
                                else:
                                    st.session_state.enhanced_context = enhanced_context
                            
                            # Show preview of extracted content
                            with st.expander("👀 Preview extracted content"):
                                preview_text = extracted_content[:1500] + "..." if len(extracted_content) > 1500 else extracted_content
                                st.text_area("Extracted content:", preview_text, height=200, disabled=True)
    
    with tab2:
        st.markdown("**Upload images to include directly in your slides**")
        
        slide_images = st.file_uploader(
            "Choose images for slides",
            type=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
            accept_multiple_files=True,
            help="Upload charts, graphs, photos, or any images you want to appear in your presentation slides",
            key="slide_images"
        )
        
        processed_slide_images = []
        if slide_images:
            valid_slide_images = validate_slide_images(slide_images)
            if valid_slide_images:
                with st.spinner("🖼️ Processing images for slides..."):
                    processed_slide_images = process_slide_images(valid_slide_images)
                    if processed_slide_images:
                        st.success(f"✅ Processed {len(processed_slide_images)} image(s) for slides")
                        
                        # Display image previews
                        display_image_preview(processed_slide_images)
                        
                        # Show image relevance analysis if user goals are available
                        if user_goals:
                            st.markdown("#### 🎯 Image Relevance Analysis")
                            relevance_scores = calculate_content_image_relevance(user_goals, processed_slide_images)
                            
                            if relevance_scores:
                                for score_info in relevance_scores:
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**{score_info['image_name']}**")
                                        if score_info['keywords']:
                                            st.caption(f"Keywords: {', '.join(score_info['keywords'])}")
                                        if score_info['common_themes']:
                                            st.caption(f"🎯 Common themes: {', '.join(score_info['common_themes'])}")
                                    
                                    with col2:
                                        score = score_info['similarity_score']
                                        if score > 0.5:
                                            st.success(f"{score:.1%}")
                                        elif score > 0.3:
                                            st.info(f"{score:.1%}")
                                        else:
                                            st.warning(f"{score:.1%}")
                        
                        # Store processed images in session state
                        st.session_state.slide_images = processed_slide_images
    
    # Set content for generation (combine goals with extracted content if available)
    if user_goals:
        if 'enhanced_context' in st.session_state:
            content = st.session_state.enhanced_context
        else:
            content = user_goals
    else:
        content = ""

with col2:
    st.subheader("⚙️ Presentation Settings")
    
    # Presentation type
    pres_type = st.selectbox(
        "Presentation Type",
        list(config.PRESENTATION_DEFAULTS.keys())
    )
    
    # Get defaults
    defaults = config.PRESENTATION_DEFAULTS[pres_type]
    
    # Slide count
    slide_count = st.slider(
        "Number of slides",
        min_value=5,
        max_value=50,
        value=defaults["slides"],
        help=f"Recommended: {defaults['slides']} slides for {pres_type}"
    )
    
    # Template selection
    template = st.selectbox(
        "Visual Style",
        config.TEMPLATE_STYLES,
        help="Choose a design that matches your presentation context"
    )
    
    # Advanced options (collapsed by default)
    with st.expander("🔧 Advanced Options"):
        include_citations = st.checkbox("Include citations slide", value=True)
        include_questions = st.checkbox("Include Q&A slide", value=True)
        speaker_notes = st.checkbox("Generate speaker notes", value=True)

# Generate button
if st.button("🚀 Generate Presentation", type="primary", use_container_width=True):
    if not config.OPENAI_API_KEY:
        st.error("❌ Please configure your OpenAI API key in the sidebar!")
    elif not user_goals:
        st.error("❌ Please describe your presentation goals and objectives!")
    else:
        # Show hint for short content but don't block generation
        if len(user_goals) < 50:
            st.info("💡 Tip: Adding more details about your goals and target audience will help generate better slides!")
        
        # Show content analysis summary if available
        if 'enhanced_context' in st.session_state:
            st.info("🎯 Using enhanced context from your uploaded materials for better slide generation!")
        try:
            with st.spinner("🔮 Creating your presentation... (30-60 seconds)"):
                # Store generation parameters for potential regeneration
                st.session_state.content = content
                st.session_state.user_goals = user_goals
                st.session_state.slide_count = slide_count
                st.session_state.pres_type = pres_type
                
                # Generate slides with enhanced context and images
                slide_images_for_ai = st.session_state.get('slide_images', [])
                st.session_state.generated_slides = generate_presentation_content(
                    content=content,
                    slide_count=slide_count,
                    pres_type=pres_type,
                    input_type="Enhanced Goals & Context",
                    slide_images=slide_images_for_ai
                )
                
                # Apply intelligent image-to-slide matching using similarity analysis
                if slide_images_for_ai:
                    st.session_state.generated_slides = analyze_image_slide_similarity(
                        st.session_state.generated_slides, 
                        slide_images_for_ai
                    )
                    # Include slide images for PPTX generation
                    st.session_state.generated_slides['slide_images'] = slide_images_for_ai
                
                st.success("✅ Presentation generated successfully!")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Tip: Check your API key and try again")

# Display generated slides (if any)
# In app.py, find this section and replace it:

# Display generated slides (if any)
if st.session_state.generated_slides:
    st.markdown("---")
    st.subheader("📊 Preview Your Presentation")
    
    # Add tabs for better organization
    tab1, tab2 = st.tabs(["📑 Slide Preview", "📝 Full Content"])
    
    with tab1:
        # Display slides in a nice format
        slides = st.session_state.generated_slides.get('slides', [])
        
        # Display presentation title with edit option
        if 'title' in st.session_state.generated_slides:
            col_title, col_edit_title = st.columns([4, 1])
            with col_title:
                st.markdown(f"## 🎯 {st.session_state.generated_slides['title']}")
            with col_edit_title:
                if st.button("✏️ Edit Title", key="edit_title_btn"):
                    st.session_state.editing_title = True
            
            # Title editing interface
            if st.session_state.get('editing_title', False):
                new_title = st.text_input("Edit Presentation Title:", 
                                        value=st.session_state.generated_slides['title'],
                                        key="title_input")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Save Title", key="save_title"):
                        st.session_state.generated_slides['title'] = new_title
                        st.session_state.editing_title = False
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Cancel", key="cancel_title"):
                        st.session_state.editing_title = False
                        st.rerun()
            
            st.markdown("---")
        
        # Slide management buttons
        col_add, col_regen = st.columns(2)
        with col_add:
            if st.button("➕ Add New Slide", key="add_slide_btn"):
                new_slide_number = len(slides) + 1
                new_slide = {
                    "number": new_slide_number,
                    "title": "New Slide",
                    "content": ["Add your content here"],
                    "notes": "Add speaker notes here"
                }
                slides.append(new_slide)
                st.rerun()
        
        with col_regen:
            if st.button("🔄 Regenerate All Slides", key="regen_slides_btn"):
                if st.session_state.get('content'):
                    try:
                        with st.spinner("🔮 Regenerating presentation..."):
                            st.session_state.generated_slides = generate_presentation_content(
                                content=st.session_state.get('content', ''),
                                slide_count=st.session_state.get('slide_count', 10),
                                pres_type=st.session_state.get('pres_type', 'Lab Meeting'),
                                input_type=st.session_state.get('input_type', 'Abstract/Summary')
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error regenerating: {str(e)}")
        
        st.markdown("---")
        
        # Create a container for slides
        for i, slide in enumerate(slides):
            with st.container():
                col1, col2, col3 = st.columns([1, 8, 1])
                
                with col1:
                    st.markdown(f"### {slide.get('number', i+1)}")
                
                with col2:
                    # Check if this slide is being edited
                    slide_key = f"slide_{i}"
                    is_editing = st.session_state.get(f'editing_{slide_key}', False)
                    
                    if not is_editing:
                        # Display mode
                        st.markdown(f"### {slide.get('title', 'Untitled Slide')}")
                        
                        # Display content properly - clean up formatting
                        content_items = slide.get('content', [])
                        if isinstance(content_items, list):
                            for item in content_items:
                                # Clean up the bullet point formatting
                                clean_item = str(item).strip()
                                # Remove existing bullet points and dashes
                                if clean_item.startswith('- '):
                                    clean_item = clean_item[2:].strip()
                                elif clean_item.startswith('• '):
                                    clean_item = clean_item[2:].strip()
                                st.markdown(f"• {clean_item}")
                        else:
                            clean_item = str(content_items).strip()
                            if clean_item.startswith('- '):
                                clean_item = clean_item[2:].strip()
                            st.markdown(f"• {clean_item}")
                        
                        # Show suggested image if available
                        if slide.get('suggested_image'):
                            image_name = slide['suggested_image']
                            similarity_score = slide.get('image_similarity_score', 0)
                            
                            col_img, col_score = st.columns([3, 1])
                            with col_img:
                                st.markdown(f"🖼️ **Suggested Image**: {image_name}")
                            with col_score:
                                if similarity_score > 0.5:
                                    st.success(f"Match: {similarity_score:.1%}")
                                elif similarity_score > 0.3:
                                    st.info(f"Match: {similarity_score:.1%}")
                                else:
                                    st.warning(f"Match: {similarity_score:.1%}")
                        
                        # Show speaker notes in an expander
                        if slide.get('notes'):
                            with st.expander("👤 Speaker Notes"):
                                st.caption(slide['notes'])
                    
                    else:
                        # Edit mode
                        st.markdown("### 📝 Editing Slide")
                        
                        # Edit slide title
                        new_title = st.text_input("Slide Title:", 
                                                value=slide.get('title', ''),
                                                key=f"edit_title_{i}")
                        
                        # Edit content
                        st.write("**Content Points:**")
                        content_items = slide.get('content', [])
                        
                        # Initialize content tracking in session state if not exists
                        content_key = f"slide_content_{i}"
                        if content_key not in st.session_state:
                            st.session_state[content_key] = [str(item).strip().lstrip('- ').lstrip('• ') for item in content_items]
                        
                        # Add new content point
                        if st.button(f"➕ Add Point", key=f"add_point_{i}"):
                            st.session_state[content_key].append("")
                            st.rerun()
                        
                        # Show content for editing
                        new_content = []
                        for j, item in enumerate(st.session_state[content_key]):
                            edited_item = st.text_area(f"Point {j+1}:", 
                                                     value=item,
                                                     key=f"edit_content_{i}_{j}",
                                                     height=80)
                            new_content.append(edited_item)
                            
                            # Add remove button for each point (except if it's the only one)
                            if len(st.session_state[content_key]) > 1:
                                if st.button(f"🗑️ Remove Point {j+1}", key=f"remove_point_{i}_{j}"):
                                    st.session_state[content_key].pop(j)
                                    st.rerun()
                        
                        # Edit speaker notes
                        new_notes = st.text_area("Speaker Notes:", 
                                                value=slide.get('notes', ''),
                                                key=f"edit_notes_{i}",
                                                height=100)
                        
                        # Save/Cancel buttons
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾 Save Changes", key=f"save_{i}"):
                                # Update the slide data
                                slides[i]['title'] = new_title
                                slides[i]['content'] = [item for item in new_content if item.strip()]
                                slides[i]['notes'] = new_notes
                                st.session_state[f'editing_{slide_key}'] = False
                                # Clean up the temporary content state
                                if content_key in st.session_state:
                                    del st.session_state[content_key]
                                st.rerun()
                        
                        with col_cancel:
                            if st.button("❌ Cancel", key=f"cancel_{i}"):
                                st.session_state[f'editing_{slide_key}'] = False
                                # Clean up the temporary content state
                                if content_key in st.session_state:
                                    del st.session_state[content_key]
                                st.rerun()
                
                with col3:
                    if not st.session_state.get(f'editing_{slide_key}', False):
                        col_edit, col_delete = st.columns(2)
                        with col_edit:
                            if st.button("✏️", key=f"edit_btn_{i}", help="Edit slide"):
                                st.session_state[f'editing_{slide_key}'] = True
                                st.rerun()
                        with col_delete:
                            if len(slides) > 1:  # Don't allow deleting if only one slide
                                if st.button("🗑️", key=f"delete_btn_{i}", help="Delete slide"):
                                    slides.pop(i)
                                    # Renumber slides
                                    for j, slide in enumerate(slides):
                                        slide['number'] = j + 1
                                    st.rerun()
                
                st.markdown("---")
    
    with tab2:
        # Show raw content for debugging
        st.json(st.session_state.generated_slides)
    
    # Download section
    col_download1, col_download2 = st.columns(2)
    
    with col_download1:
        if st.button("📊 Download as PPTX", type="primary", use_container_width=True):
            try:
                # Generate PPTX
                pptx_buffer = create_pptx_buffer(st.session_state.generated_slides)
                
                # Create download button for PPTX
                st.download_button(
                    "📥 Click to Download PPTX",
                    pptx_buffer.getvalue(),
                    file_name=f"{st.session_state.generated_slides.get('title', 'presentation').replace(' ', '_')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
                st.success("✅ PPTX generated successfully!")
            except Exception as e:
                st.error(f"❌ Error generating PPTX: {str(e)}")
    
    with col_download2:
        if st.button("📄 Download as PDF", type="secondary", use_container_width=True):
            try:
                # Generate PDF
                pdf_buffer = create_pdf_from_slides(st.session_state.generated_slides)
                
                # Create download button for PDF
                st.download_button(
                    "📥 Click to Download PDF",
                    pdf_buffer.getvalue(),
                    file_name=f"{st.session_state.generated_slides.get('title', 'presentation').replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF generated successfully!")
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
                
                # Fallback: create text version
                slides_text = f"{st.session_state.generated_slides.get('title', 'Presentation')}\n{'='*50}\n\n"
                
                for s in slides:
                    slide_text = f"Slide {s.get('number', '')}: {s.get('title', 'Untitled')}\n"
                    slide_text += "-" * 30 + "\n"
                    
                    # Clean up content formatting
                    content_items = s.get('content', [])
                    if isinstance(content_items, list):
                        for item in content_items:
                            clean_item = str(item).strip()
                            if clean_item.startswith('- '):
                                clean_item = clean_item[2:].strip()
                            elif clean_item.startswith('• '):
                                clean_item = clean_item[2:].strip()
                            slide_text += f"  • {clean_item}\n"
                    else:
                        clean_item = str(content_items).strip()
                        if clean_item.startswith('- '):
                            clean_item = clean_item[2:].strip()
                        slide_text += f"  • {clean_item}\n"
                    
                    # Add speaker notes if available
                    if s.get('notes'):
                        slide_text += f"\nSpeaker Notes: {s.get('notes')}\n"
                    
                    slides_text += slide_text + "\n\n"
                
                st.download_button(
                    "📄 Download as Text (Fallback)",
                    slides_text,
                    file_name="presentation.txt",
                    mime="text/plain",
                    use_container_width=True
                )