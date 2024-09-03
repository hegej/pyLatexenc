import json
import re
import os
from datetime import datetime
from typing import List, Dict, Any


LATEX_PATTERN = re.compile(r'''
    (
        \\(begin|end)\{[^}]+\}  # \begin{...} or \end{...} as a single unit
        |\\([a-zA-Z]+)(\*)?     # Other command names (including optional *)
        (\[[^\]]*\])?           # Optional parameter in square brackets
        (\{(?:[^{}]|\{[^{}]*\})*\})?  # Content in curly braces, allowing one level of nesting
        |\{|\}                  # Unmatched curly braces
        |\[|\]                  # Unmatched square brackets
        |\\[                    # Start of a math block
        |\$\$?                  # Math mode (inline or display)
        |%[^\n]*                # Comments
        |\\.                    # Escaped characters
        |&                      # Table column separator
        |\\\\                   # Table row separator
        |[ \t]+                 # Explicit whitespace
        |\n+                    # One or more newlines
        |[^\\{}\[\]$%&\s]+      # Plain text (excluding whitespace and table separators)
    )
''', re.VERBOSE)

def is_punctuation(token: str) -> bool:
    return len(token) == 1 and token in '.,;:!?()-'

def is_filepath_or_filename(token: str) -> bool:
    return bool(re.match(r'[\w\-./\\]+\.(tex|eps|pdf|png|jpg|jpeg)$', token, re.IGNORECASE))

def is_latex_command(token: str) -> bool:
    return token.startswith('\\') and not token.startswith('\\begin') and not token.startswith('\\end')

def get_token_type(token: str) -> str:
    if token.startswith(('\\begin', '\\end')):
        return 'environment'
    elif token.startswith(('\\chapter', '\\section', '\\subsection', '\\subsubsection', '\\paragraph', '\\subparagraph', '\\emph', '\\textbf', '\\note')):
        return 'structure'
    elif token.startswith(('\\newcommand', '\\renewcommand', '\\def')):
        return 'define'
    elif is_latex_command(token):
        return 'command'
    elif token in ['{', '}', '[', ']']:
        return 'bracket'
    elif token in ['\\[', '\\]', '$', '$$']:
        return 'math'
    elif token in ['&', '\\\\']:
        return 'table_separator'
    elif token.startswith('%'):
        return 'comment'
    elif token.isspace():
        return 'whitespace' if '\n' not in token else 'newline'
    elif is_filepath_or_filename(token):
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
        
        if token_type == 'environment':
            tokens.append({
                'type': token_type,
                'value': token,
                'line': line,
                'position': (token_start, token_end),
                'multiline': False,
                'block': 0
            })
        elif token_type in ['structure', 'command']:
            command_end = token.find('{') if '{' in token else None
            if command_end is not None:

                tokens.append({
                    'type': token_type,
                    'value': token[:command_end],
                    'line': line,
                    'position': (token_start, token_start + command_end),
                    'multiline': False,
                    'block': 0 
                })

                tokens.append({
                    'type': 'bracket',
                    'value': '{',
                    'line': line,
                    'position': (token_start + command_end, token_start + command_end + 1),
                    'multiline': False,
                    'block': 0
                })

                inner_content = token[command_end+1:-1]
                inner_tokens = tokenize_content(inner_content, line, token_start + command_end + 1)
                tokens.extend(inner_tokens)
                tokens.append({
                    'type': 'bracket',
                    'value': '}',
                    'line': line,
                    'position': (token_end - 1, token_end),
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
        else:
            tokens.append({
                'type': token_type,
                'value': token,
                'line': line,
                'position': (token_start, token_end),
                'multiline': False,
                'block': 0  
            })
        
        if token_type == 'newline':
            line += token.count('\n')
    
    return tokens

def tokenize_latex(text: str) -> List[Dict[str, Any]]:
    tokens = []
    block_stack = [0]
    current_block = 0
    
    line_tokens = tokenize_content(text, 1, 0)
    for token in line_tokens:
        if token['type'] in ['structure', 'environment'] and token['value'].startswith('\\begin'):
            current_block += 1
            block_stack.append(current_block)
        elif token['type'] == 'environment' and token['value'].startswith('\\end') and len(block_stack) > 1:
            block_stack.pop()
            current_block = block_stack[-1]
        
        token['block'] = block_stack[-1]
        tokens.append(token)

    return tokens

def detokenize_latex(tokens: List[Dict[str, Any]]) -> str:
    return ''.join(token['value'] for token in tokens)

def mock_translate(text: str) -> str:
    return text + " (oversatt)"

def consolidate_text_tokens(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    consolidated = []
    current_text = []
    current_text_start = None
    current_line = None
    
    for token in tokens:
        if token['type'] == 'text':
            if not current_text:
                current_text_start = token['position'][0]
                current_line = token['line']
            current_text.append(token['value'])
        else:
            if current_text:
                consolidated.append({
                    'type': 'text_block',
                    'value': ' '.join(current_text),
                    'line': current_line,
                    'position': (current_text_start, token['position'][0]),
                    'multiline': False,
                    'block': token['block']
                })
                current_text = []
            consolidated.append(token)
    
    if current_text:
        consolidated.append({
            'type': 'text_block',
            'value': ' '.join(current_text),
            'line': current_line,
            'position': (current_text_start, tokens[-1]['position'][1]),
            'multiline': False,
            'block': tokens[-1]['block']
        })
    
    return consolidated

def split_text_block(original: str, translated: str) -> List[str]:
    # This is a simple split strategy. May need a more sophisticated one
    # depending on how your translation API behaves.
    original_words = original.split()
    translated_words = translated.split()
    
    if len(original_words) == len(translated_words):
        return translated_words
    else:
        # If word count doesn't match, we'll have to use a different strategy
        # For now, we'll just return the full translated text as one item
        return [translated]

def translate_latex_document(latex_text: str) -> str:
    tokens = tokenize_latex(latex_text)
    consolidated_tokens = consolidate_text_tokens(tokens)
    translated_tokens = []
    in_table = False
    
    for token in consolidated_tokens:
        if token['type'] == 'environment':
            if 'tabular' in token['value'] or 'table' in token['value']:
                in_table = '\\begin' in token['value']
        
        if token['type'] == 'text_block':
            if not in_table or (in_table and not token['value'].strip().startswith('\\')):
                translated_text = mock_translate(token['value'])
                split_text = split_text_block(token['value'], translated_text)
                
                start = token['position'][0]
                for word in split_text:
                    translated_tokens.append({
                        'type': 'text',
                        'value': word,
                        'line': token['line'],
                        'position': (start, start + len(word)),
                        'multiline': False,
                        'block': token['block']
                    })
                    start += len(word) + 1 
            else:
                translated_tokens.append(token)
        else:
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
    input_file = r"C:\Dev\AKVA_connect_manuals\User manual\src\english\chapters\camera_view\camera_view.tex"
    
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

    original_filename = os.path.join(output_dir, f"original_latex_{timestamp}.tex")
    write_to_file(latex_text, original_filename)
    print(f"Original LaTeX document written to: {original_filename}")

    tokens = tokenize_latex(latex_text)
    tokens_filename = os.path.join(output_dir, f"tokens_{timestamp}.json")
    write_to_json(tokens, tokens_filename)
    print(f"Tokens written to JSON file: {tokens_filename}")

    translated_document = translate_latex_document(latex_text)
    translated_filename = os.path.join(output_dir, f"translated_latex_{timestamp}.tex")
    write_to_file(translated_document, translated_filename)
    print(f"Translated LaTeX document written to: {translated_filename}")

if __name__ == "__main__":
    main()