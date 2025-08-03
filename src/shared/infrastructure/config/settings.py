from dataclasses import dataclass


@dataclass
class AppSettings:
    host: str = '0.0.0.0'
    port: int = 5001
    debug: bool = True
    max_content_length: int = 100 * 1024 * 1024  # 100MB
    json_as_ascii: bool = False