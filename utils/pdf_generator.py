from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, darkblue
import io
from PIL import Image as PILImage

def create_pdf_from_slides(slides_data, template="Modern Research"):
    """
    Create a PDF from slides data
    """
    # Create a BytesIO buffer to hold the PDF
    buffer = io.BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Get default styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=darkblue,
        alignment=1  # Center alignment
    )
    
    slide_title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=blue,
        leftIndent=0
    )
    
    slide_number_style = ParagraphStyle(
        'SlideNumber',
        parent=styles['Normal'],
        fontSize=12,
        textColor=blue,
        alignment=2  # Right alignment
    )
    
    content_style = ParagraphStyle(
        'Content',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leftIndent=20,
        bulletIndent=15
    )
    
    notes_style = ParagraphStyle(
        'Notes',
        parent=styles['Normal'],
        fontSize=9,
        textColor=black,
        leftIndent=20,
        spaceAfter=12,
        fontName='Helvetica-Oblique'
    )
    
    # Add presentation title
    presentation_title = slides_data.get('title', 'Presentation')
    elements.append(Paragraph(presentation_title, title_style))
    elements.append(Spacer(1, 20))
    
    # Add slides
    slides = slides_data.get('slides', [])
    slide_images = slides_data.get('slide_images', [])
    image_lookup = {img['name']: img for img in slide_images} if slide_images else {}
    
    for i, slide in enumerate(slides):
        # Add slide number
        slide_num = slide.get('number', i + 1)
        elements.append(Paragraph(f"Slide {slide_num}", slide_number_style))
        
        # Add slide title
        slide_title = slide.get('title', 'Untitled Slide')
        elements.append(Paragraph(slide_title, slide_title_style))
        
        # Add slide content
        content_items = slide.get('content', [])
        if isinstance(content_items, list):
            for item in content_items:
                clean_item = str(item).strip()
                # Clean up formatting
                if clean_item.startswith('- '):
                    clean_item = clean_item[2:].strip()
                elif clean_item.startswith('• '):
                    clean_item = clean_item[2:].strip()
                
                elements.append(Paragraph(f"• {clean_item}", content_style))
        else:
            clean_item = str(content_items).strip()
            if clean_item.startswith('- '):
                clean_item = clean_item[2:].strip()
            elements.append(Paragraph(f"• {clean_item}", content_style))
        
        # Add image if suggested and available
        suggested_image = slide.get('suggested_image', '')
        if suggested_image and suggested_image in image_lookup:
            try:
                image_info = image_lookup[suggested_image]
                image_bytes = image_info['bytes']
                
                # Create image stream
                image_stream = io.BytesIO(image_bytes)
                
                # Add image to PDF
                # Resize image to fit page width
                img = Image(image_stream)
                img.drawHeight = 3*inch  # Fixed height
                img.drawWidth = 4*inch   # Fixed width
                
                elements.append(Spacer(1, 10))
                elements.append(img)
                elements.append(Spacer(1, 10))
                
            except Exception as e:
                # If image fails, add text note
                elements.append(Paragraph(f"<i>Image: {suggested_image} (could not be embedded)</i>", notes_style))
        
        # Add speaker notes if available
        if slide.get('notes'):
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>Speaker Notes:</b> {slide['notes']}", notes_style))
        
        # Add spacing between slides (but not after the last slide)
        if i < len(slides) - 1:
            elements.append(Spacer(1, 30))
            elements.append(PageBreak())
    
    # Build the PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    buffer.seek(0)
    return buffer 