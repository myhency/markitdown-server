import re


class MarkdownEnhancerService:
    
    def enhance_markdown_structure(self, text: str, filename: str) -> str:
        if not text or not text.strip():
            return text
        
        lines = text.split('\n')
        enhanced_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if not line:
                enhanced_lines.append('')
                continue
                
            if '<' in line and '@' in line and '>' in line:
                email_pattern = r'<([^@]+@[^>]+)>'
                line = re.sub(email_pattern, r'[\1](mailto:\1)', line)
                enhanced_lines.append(line)
                continue
            
            if (i == 0 and len(line) > 10) or any(keyword in line for keyword in ['확인서', '증명서', '참가', 'Conference', 'Certificate']):
                enhanced_lines.append(f'# {line}')
                enhanced_lines.append('')
                continue
                
            if re.search(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일', line) or re.search(r'\d{1,2}월\s*\d{1,2}일', line):
                enhanced_lines.append(f'**{line}**')
                continue
                
            if ':' in line and len(line.split(':')) == 2:
                parts = line.split(':', 1)
                key = parts[0].strip()
                value = parts[1].strip()
                enhanced_lines.append(f'**{key}**: {value}')
                continue
                
            if len(line) < 20 and any(keyword in line for keyword in ['성명', '이름', '날짜', '시간', '장소']):
                enhanced_lines.append(f'**{line}**')
                continue
                
            enhanced_lines.append(line)
        
        result_lines = []
        prev_empty = False
        
        for line in enhanced_lines:
            is_empty = not line.strip()
            if not (is_empty and prev_empty):
                result_lines.append(line)
            prev_empty = is_empty
        
        return '\n'.join(result_lines)