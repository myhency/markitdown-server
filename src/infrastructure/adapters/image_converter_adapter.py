import os
import tempfile
import subprocess
import shutil
import logging
from typing import List
from io import BytesIO
from ...application.ports.image_processor import ImageProcessorPort
from ...domain.exceptions.conversion_exceptions import ImageConversionException

logger = logging.getLogger(__name__)


class ImageConverterAdapter(ImageProcessorPort):
    
    def convert_pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[bytes]:
        try:
            from pdf2image import convert_from_path
            from PIL import Image
            
            images = convert_from_path(pdf_path, dpi=dpi)
            
            image_bytes_list = []
            for i, image in enumerate(images):
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='PNG')
                image_bytes_list.append(img_byte_arr.getvalue())
                logger.info(f"Converted page {i+1} to image")
            
            return image_bytes_list
        
        except ImportError:
            raise ImageConversionException("pdf2image package is required. Install with: pip install pdf2image")
        except Exception as e:
            raise ImageConversionException(f"Failed to convert PDF to images: {str(e)}")
    
    def convert_office_to_pdf(self, file_path: str, file_extension: str) -> str:
        try:
            temp_dir = tempfile.mkdtemp()
            try:
                cmd = [
                    'libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', temp_dir, file_path
                ]
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info(f"LibreOffice PDF conversion output: {result.stdout}")
                
                pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
                
                if not pdf_files:
                    raise ImageConversionException(f"No PDF file generated in {temp_dir}")
                
                pdf_path = os.path.join(temp_dir, pdf_files[0])
                logger.info(f"Successfully converted {file_extension} to PDF: {pdf_path}")
                
                return pdf_path
            
            except subprocess.CalledProcessError as e:
                logger.error(f"LibreOffice PDF conversion failed: {e.stderr}")
                raise ImageConversionException(f"Failed to convert {file_extension} to PDF: {e.stderr}")
                
        except Exception as e:
            logger.error(f"Office to PDF conversion error: {str(e)}")
            raise ImageConversionException(f"Failed to convert {file_extension} to PDF: {str(e)}")
    
    def convert_office_document_to_images(self, file_path: str, file_extension: str, dpi: int = 200) -> List[bytes]:
        temp_pdf_path = None
        temp_dir = None
        
        try:
            logger.info(f"Converting {file_extension} to PDF first...")
            temp_pdf_path = self.convert_office_to_pdf(file_path, file_extension)
            temp_dir = os.path.dirname(temp_pdf_path)
            
            logger.info(f"Converting PDF to images with DPI {dpi}...")
            image_bytes_list = self.convert_pdf_to_images(temp_pdf_path, dpi=dpi)
            
            logger.info(f"Successfully converted {file_extension} → PDF → {len(image_bytes_list)} images")
            return image_bytes_list
            
        except Exception as e:
            logger.error(f"Office document conversion failed: {str(e)}")
            logger.info("Falling back to basic image generation...")
            return self.convert_document_to_images_basic(file_path)
            
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean up temporary directory {temp_dir}: {e}")
    
    def convert_document_to_images_basic(self, file_path: str) -> List[bytes]:
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            text = f"Document: {os.path.basename(file_path)}\nConverted to image placeholder"
            draw.text((50, 50), text, fill='black', font=font)
            
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            
            return [img_byte_arr.getvalue()]
        
        except Exception as e:
            raise ImageConversionException(f"Failed basic image conversion: {str(e)}")