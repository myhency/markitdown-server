class ConversionException(Exception):
    """Base exception for conversion errors"""
    pass


class UnsupportedFileFormatException(ConversionException):
    """Exception for unsupported file formats"""
    pass


class ConversionFailedException(ConversionException):
    """Exception for conversion failures"""
    pass


class AIClientException(ConversionException):
    """Exception for AI client errors"""
    pass


class ImageConversionException(ConversionException):
    """Exception for image conversion errors"""
    pass


class FileProcessingException(ConversionException):
    """Exception for file processing errors"""
    pass