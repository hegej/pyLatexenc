import json
from pylatexenc.latexwalker import LatexWalker, LatexWalkerParseError, LatexEnvironmentNode, LatexMacroNode, LatexCharsNode, LatexGroupNode

def read_latex_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def parse_latex(latex_content):
    walker = LatexWalker(latex_content)
    try:
        nodes, _, _ = walker.get_latex_nodes(pos=0)
        return nodes
    except LatexWalkerParseError as e:
        print("Error parsing LaTeX:", e)
        return []

def extract_segments(nodes, latex_content):
    segments = []
    for node in nodes:
        line_number = latex_content[:node.pos].count('\n') + 1  # Calculate the line number
        if isinstance(node, LatexCharsNode):
            segments.append({"type": "text", "content": node.chars, "line": line_number})
        elif isinstance(node, LatexGroupNode) or isinstance(node, LatexEnvironmentNode):
            if node.nodelist:
                content_type = "group" if isinstance(node, LatexGroupNode) else "environment"
                environment_name = node.environmentname if isinstance(node, LatexEnvironmentNode) else None
                segment = {"type": content_type, "content": extract_segments(node.nodelist, latex_content), "line": line_number}
                if environment_name:
                    segment["name"] = environment_name
                segments.append(segment)
        elif isinstance(node, LatexMacroNode):
            macro_content = {
                "type": "macro",
                "name": node.macroname,
                "args": [],
                "line": line_number
            }
            if node.nodeargd and node.nodeargd.argnlist:
                for arg in node.nodeargd.argnlist:
                    if arg and hasattr(arg, 'nodelist'):
                        macro_content["args"].append(extract_segments(arg.nodelist, latex_content))
                    else:
                        macro_content["args"].append([])
            segments.append(macro_content)
    return segments

def reconstruct_latex(segments):
    latex_content = ""
    for segment in segments:
        if segment["type"] == "text":
            latex_content += segment["content"]
        elif segment["type"] == "group":
            latex_content += "{" + reconstruct_latex(segment["content"]) + "}"
        elif segment["type"] == "environment":
            latex_content += f"\\begin{{{segment['name']}}}"
            latex_content += reconstruct_latex(segment["content"])
            latex_content += f"\\end{{{segment['name']}}}\n"
        elif segment["type"] == "macro":
            latex_content += f"\\{segment['name']}"
            for arg in segment["args"]:
                latex_content += "{" + reconstruct_latex(arg) + "}" if arg else ""
    return latex_content

def write_json(output_path, data):
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)

def main():
    latex_file_path = r'C:\Users\hejacobsen\OneDrive - AKVA Group\Documents\TEX\Barge_control.tex'
    output_json_path = r'C:\Users\hejacobsen\OneDrive - AKVA Group\Documents\TEX\Output\latex_output_barge.json'
    text_only_output_path = r'C:\Users\hejacobsen\OneDrive - AKVA Group\Documents\TEX\Output\text_only_output_barge.json'
    reconstructed_tex_path = r'C:\Users\hejacobsen\OneDrive - AKVA Group\Documents\TEX\Output\Reconstructed_barge.tex'

    latex_content = read_latex_file(latex_file_path)
    nodes = parse_latex(latex_content)
    segments = extract_segments(nodes, latex_content)

    write_json(output_json_path, segments)
    text_only = [{"line": seg["line"], "content": seg["content"]} for seg in segments if seg["type"] == "text"]
    write_json(text_only_output_path, text_only)

    reconstructed_latex = reconstruct_latex(segments)
    with open(reconstructed_tex_path, 'w', encoding='utf-8') as tex_file:
        tex_file.write(reconstructed_latex)

    print(f"Full JSON output has been written to {output_json_path}")
    print(f"Text-only JSON output has been written to {text_only_output_path}")
    print(f"Reconstructed LaTeX file has been written to {reconstructed_tex_path}")

if __name__ == "__main__":
    main()