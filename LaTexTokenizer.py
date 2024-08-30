import re
import os
from datetime import datetime

def tokenize_latex(text):
    tokens = []
    pattern = r'''
        (
            \\begin\{[^}]+\}  # \begin{...}
            |\\end\{[^}]+\}    # \end{...}
            |\\[a-zA-Z]+\*?  # LaTeX-kommandoer, inkludert de med stjerne
            |\{|\}          # Krøllparenteser
            |\[|\]          # Firkantparenteser
            |\\[                 # Starten på en matematisk blokk
            |\$\$?               # Matematisk modus (inline eller display)
            |\\[a-zA-Z]+\{[^}]*\}  # Kommandoer med argumenter
            |%[^\n]*             # Kommentarer
            |\\.                 # Escapet tegn
            |[^\\{}\[\]$%\n]+    # Vanlig tekst
            |\n                  # Linjeskift
        )
    '''
    
    lines = text.split('\n')
    block_stack = [0]
    current_block = 0

    for line_number, line in enumerate(lines, 1):
        line_tokens = list(re.finditer(pattern, line, re.VERBOSE))
        
        for i, match in enumerate(line_tokens):
            token = match.group(0)
            start, end = match.span()
            
            if token.startswith('\\begin'):
                current_block += 1  # Increment as we enter a new block
                block_stack.append(current_block)
            elif token.startswith('\\end'):
                if len(block_stack) > 1:
                    block_stack.pop() 
            
            is_multiline = (i == len(line_tokens) - 1 and token != '\n' and line_number < len(lines))
            
            token_info = {
                'type': 'begin' if token.startswith('\\begin') else
                        'end' if token.startswith('\\end') else
                        'command' if token.startswith('\\') or token in ['{', '}', '[', ']', '\\[', '$', '$$'] else
                        'comment' if token.startswith('%') else
                        'newline' if token == '\n' else 'text',
                'value': token,
                'line': line_number,
                'position': (start, end),
                'multiline': is_multiline,
                'block': block_stack[-1],
                'nesting_level': len(block_stack)  # Add nesting level here
            }
            
            tokens.append(token_info)

    return tokens

def detokenize_latex(tokens):
    return ''.join(token['value'] for token in tokens)

def mock_translate(text):
    return text + " (oversatt)"

def translate_latex_document(latex_text):
    tokens = tokenize_latex(latex_text)
    translated_tokens = []
    
    for token in tokens:
        if token['type'] == 'text':
            token['value'] = mock_translate(token['value'])
        translated_tokens.append(token)
    
    return detokenize_latex(translated_tokens)

def write_to_file(content, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)

def main():
    input_file = r"C:\Dev\AKVA_connect_manuals\User manual\src\english\chapters\barge_control\barge_control.tex"
    
    # Read the LaTeX document
    with open(input_file, 'r', encoding='utf-8') as file:
        latex_text = file.read()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = r"C:\temp"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Write original LaTeX document
    original_filename = os.path.join(output_dir, f"original_latex_{timestamp}.tex")
    write_to_file(latex_text, original_filename)
    print(f"Original LaTeX document written to: {original_filename}")

    # Tokenize and write tokens
    tokens = tokenize_latex(latex_text)
    tokens_filename = os.path.join(output_dir, f"tokens_{timestamp}.txt")
    tokens_content = "\n".join([f"Type: {token['type']}, Value: {token['value']}, Line: {token['line']}, "
                                f"Position: {token['position']}, Multiline: {token['multiline']}, "
                                f"Block: {token['block']}"
                                for token in tokens])
    write_to_file(tokens_content, tokens_filename)
    print(f"Tokens written to: {tokens_filename}")

    # Translate and write translated document
    translated_document = translate_latex_document(latex_text)
    translated_filename = os.path.join(output_dir, f"translated_latex_{timestamp}.tex")
    write_to_file(translated_document, translated_filename)
    print(f"Translated LaTeX document written to: {translated_filename}")

if __name__ == "__main__":
    main()