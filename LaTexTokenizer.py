import json
import re
import os
from datetime import datetime
from typing import List, Dict, Any

LATEX_PATTERN = re.compile(r'''
    (
        \\([a-zA-Z]+)(\*)?     # Command name (including optional *)
        (\[[^\]]*\])?          # Optional parameter in square brackets
        (\{(?:[^{}]|\{[^{}]*\})*\})?  # Content in curly braces, allowing one level of nesting
        |\\(begin|end)\{([^}]+)\}  # \begin{...} or \end{...}
        |\{|\}                 # Unmatched curly braces
        |\[|\]                 # Unmatched square brackets
        |\\[                   # Start of a math block
        |\$\$?                 # Math mode (inline or display)
        |%[^\n]*               # Comments
        |\\.                   # Escaped characters
        |[^\\{}\[\]$%\n]+      # Plain text
        |\n                    # Newline
    )
''', re.VERBOSE)

def is_punctuation(token: str) -> bool:
    return len(token) == 1 and token in '.,;:!?()-'

def get_token_type(token: str) -> str:
    if token.startswith(('\\chapter', '\\section', '\\subsection', '\\subsubsection', '\\paragraph', '\\subparagraph', '\\emph', '\\textbf', '\\note')):
        return 'structure'
    elif token.startswith('\\begin'):
        return 'begin'
    elif token.startswith('\\end'):
        return 'end'
    elif token.startswith(('\\newcommand', '\\renewcommand', '\\def')):
        return 'define'
    elif token.startswith('\\'):
        return 'command'
    elif token in ['{', '}', '[', ']']:
        return 'bracket'
    elif token in ['\\[', '\\]', '$', '$$']:
        return 'math'
    elif token.startswith('%'):
        return 'comment'
    elif token == '\n':
        return 'newline'
    elif re.match(r'\s*/[^\s]+\.(pdf|eps|png|jpg|jpeg|tex)$', token): 
        return 'filepath'
    elif re.match(r'[a-zA-Z0-9:_-]+', token) and ':' in token: 
        return 'reference'
    elif is_punctuation(token):
        return 'punctuation'
    elif token.strip(): 
        return 'text'
    else:
        return 'whitespace'

def tokenize_content(content: str, line: int, start: int) -> List[Dict[str, Any]]:
    tokens = []
    for match in LATEX_PATTERN.finditer(content):
        token = match.group(0)
        token_start = start + match.start()
        token_end = start + match.end()
        token_type = get_token_type(token)
        
        if token_type in ['structure', 'command']:
            tokens.append({
                'type': token_type,
                'value': token[:token.find('{') if '{' in token else None],
                'line': line,
                'position': (token_start, token_end),
                'multiline': False,
                'block': 0 
            })
            if match.group(5):  
                inner_content = match.group(5)[1:-1] 
                inner_tokens = tokenize_content(inner_content, line, token_start + token.index('{') + 1)
                tokens.extend(inner_tokens)
        elif token_type == 'text':
            tokens.append({
                'type': 'text',
                'value': token,
                'line': line,
                'position': (token_start, token_end),
                'multiline': False,
                'block': 0  
            })
        else:
            tokens.append({
                'type': token_type,
                'value': token,
                'line': line,
                'position': (token_start, token_end),
                'multiline': False,
                'block': 0  
            })
    return tokens

def tokenize_latex(text: str) -> List[Dict[str, Any]]:
    tokens = []
    block_stack = [0]
    current_block = 0
    
    lines = text.split('\n')
    for line_number, line in enumerate(lines, 1):
        line_tokens = tokenize_content(line, line_number, 0)
        for token in line_tokens:
            if token['type'] in ['structure', 'begin']:
                current_block += 1
                block_stack.append(current_block)
            elif token['type'] == 'end' and len(block_stack) > 1:
                block_stack.pop()
                current_block = block_stack[-1]
            
            token['block'] = block_stack[-1]
        tokens.extend(line_tokens)

    return tokens

def tokenize_latex(text: str) -> List[Dict[str, Any]]:
    tokens = []
    block_stack = [0]
    current_block = 0

    lines = text.split('\n')
    for line_number, line in enumerate(lines, 1):
        line_tokens = tokenize_content(line, line_number, 0)
        for token in line_tokens:
            if token['type'] in ['structure', 'begin']:
                current_block += 1
                block_stack.append(current_block)
            elif token['type'] == 'end' and len(block_stack) > 1:
                block_stack.pop()
                current_block = block_stack[-1]

            token['block'] = block_stack[-1]
        tokens.extend(line_tokens)

    return tokens

def detokenize_latex(tokens: List[Dict[str, Any]]) -> str:
    result = []
    for token in tokens:
        if token['type'] == 'newline':
            result.append('\n') 
        elif token['type'] == 'whitespace':
            result.append(' ') 
        else:
            result.append(token['value'])
    return ''.join(result)

def mock_translate(text: str) -> str:
    return text + " (oversatt)"

def translate_latex_document(latex_text: str) -> str:
    tokens = tokenize_latex(latex_text)
    translated_tokens = []
    
    for token in tokens:
        if token['type'] == 'text':
            token['value'] = mock_translate(token['value'])
        translated_tokens.append(token)
    
    return detokenize_latex(translated_tokens)

def write_to_file(content: str, filename: str) -> None:
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
    except IOError as e:
        print(f"Error writing to file {filename}: {e}")

def write_to_json(tokens: List[Dict[str, Any]], filename: str) -> None:
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(tokens, file, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error writing to file {filename}: {e}")


def main():
    input_file = r"C:\Dev\AKVA_connect_manuals\User manual\src\english\chapters\barge_control\barge_control.tex"
    
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            latex_text = file.read()
    except IOError as e:
        print(f"Error reading input file {input_file}: {e}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = r"C:\temp"
    
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {output_dir}: {e}")
        return

    # Skriver den originale LaTeX-dokumentet til en fil
    original_filename = os.path.join(output_dir, f"original_latex_{timestamp}.tex")
    write_to_file(latex_text, original_filename)
    print(f"Original LaTeX document written to: {original_filename}")

    # Tokeniserer og skriver tokens til JSON
    tokens = tokenize_latex(latex_text)
    tokens_filename = os.path.join(output_dir, f"tokens_{timestamp}.json")
    write_to_json(tokens, tokens_filename)
    print(f"Tokens written to JSON file: {tokens_filename}")

    # Oversetter og skriver det oversatte dokumentet
    translated_document = translate_latex_document(latex_text)
    translated_filename = os.path.join(output_dir, f"translated_latex_{timestamp}.tex")
    write_to_file(translated_document, translated_filename)
    print(f"Translated LaTeX document written to: {translated_filename}")

if __name__ == "__main__":
    main()