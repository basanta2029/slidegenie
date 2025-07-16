import streamlit as st
import PyPDF2
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io
import os

def extract_text_from_pdf(pdf_file):
    """Extract text content from uploaded PDF file"""
    try:
        # Reset file pointer
        pdf_file.seek(0)
        
        # Read PDF
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = ""
        
        # Extract text from each page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n\n"
        
        if text_content.strip():
            return text_content.strip()
        else:
            # Fallback: Try OCR if text extraction fails
            return extract_text_from_pdf_ocr(pdf_file)
            
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def extract_text_from_pdf_ocr(pdf_file):
    """Extract text from PDF using OCR (fallback method)"""
    try:
        pdf_file.seek(0)
        
        # Convert PDF to images
        images = convert_from_bytes(pdf_file.read())
        
        text_content = ""
        for i, image in enumerate(images):
            # Perform OCR on each page
            page_text = pytesseract.image_to_string(image)
            text_content += f"Page {i+1}:\n{page_text}\n\n"
        
        return text_content.strip()
        
    except Exception as e:
        st.error(f"Error with PDF OCR: {str(e)}")
        return None

def extract_text_from_image(image_file):
    """Extract text from uploaded image using OCR"""
    try:
        # Open image
        image = Image.open(image_file)
        
        # Perform OCR
        text_content = pytesseract.image_to_string(image)
        
        if text_content.strip():
            return text_content.strip()
        else:
            return "No text detected in the image."
            
    except Exception as e:
        st.error(f"Error reading image: {str(e)}")
        return None

def process_uploaded_files(uploaded_files):
    """Process multiple uploaded files and return combined text content"""
    all_content = []
    
    for file in uploaded_files:
        file_type = file.type
        file_name = file.name
        
        st.write(f"📄 Processing: {file_name}")
        
        if file_type == "application/pdf":
            content = extract_text_from_pdf(file)
            if content:
                all_content.append(f"--- Content from {file_name} ---\n{content}")
        
        elif file_type.startswith("image/"):
            content = extract_text_from_image(file)
            if content:
                all_content.append(f"--- Content from {file_name} ---\n{content}")
        
        else:
            st.warning(f"⚠️ Unsupported file type: {file_type}")
    
    return "\n\n".join(all_content) if all_content else None

def validate_file_upload(uploaded_files):
    """Validate uploaded files for size and type"""
    max_file_size = 10 * 1024 * 1024  # 10 MB
    supported_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png", "image/gif", "image/bmp"]
    
    valid_files = []
    
    for file in uploaded_files:
        # Check file size
        if file.size > max_file_size:
            st.error(f"❌ File '{file.name}' is too large. Maximum size: 10MB")
            continue
        
        # Check file type
        if file.type not in supported_types:
            st.error(f"❌ File '{file.name}' type not supported. Supported: PDF, JPG, PNG, GIF, BMP")
            continue
        
        valid_files.append(file)
    
    return valid_files

# Configuration check for OCR
def check_tesseract_config():
    """Check if Tesseract is properly configured"""
    try:
        # Test OCR with a simple check
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False 