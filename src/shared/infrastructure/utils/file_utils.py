import os
import mimetypes
from ...domain.models.file_info import FileInfo


SUPPORTED_EXTENSIONS = {
    '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
    '.pdf',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    '.wav', '.mp3',
    '.txt', '.csv', '.json', '.xml', '.html', '.htm',
    '.zip',
    '.epub',
    '.msg'
}

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
}


def is_allowed_file(filename: str) -> bool:
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)


def is_image_file(filename: str) -> bool:
    if not filename:
        return False
    extension = os.path.splitext(filename.lower())[1]
    return extension in IMAGE_EXTENSIONS


def get_file_extension(filename: str) -> str:
    if not filename:
        return ''
    return os.path.splitext(filename.lower())[1]


def allowed_file(filename: str) -> bool:
    return is_allowed_file(filename)


def get_file_info(filename: str) -> FileInfo:
    mimetype, _ = mimetypes.guess_type(filename)
    extension = os.path.splitext(filename.lower())[1]
    return FileInfo(
        filename=filename,
        extension=extension,
        mimetype=mimetype,
        supported=is_allowed_file(filename)
    )