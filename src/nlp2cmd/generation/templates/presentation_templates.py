"""
Presentation / reporting domain templates for NLP2CMD.

Contains chart generation, reports, LaTeX, Markdown, HTML rendering templates.
"""

PRESENTATION_TEMPLATES = {
    # Matplotlib / Python charts
    'chart_bar': "python3 -c \"import matplotlib.pyplot as plt; plt.bar({labels}, {values}); plt.title('{title}'); plt.savefig('{output}'); print('Saved:', '{output}')\"",
    'chart_line': "python3 -c \"import matplotlib.pyplot as plt; plt.plot({x}, {y}); plt.title('{title}'); plt.xlabel('{xlabel}'); plt.ylabel('{ylabel}'); plt.savefig('{output}')\"",
    'chart_pie': "python3 -c \"import matplotlib.pyplot as plt; plt.pie({values}, labels={labels}, autopct='%1.1f%%'); plt.title('{title}'); plt.savefig('{output}')\"",
    'chart_scatter': "python3 -c \"import matplotlib.pyplot as plt; plt.scatter({x}, {y}); plt.title('{title}'); plt.savefig('{output}')\"",
    'chart_histogram': "python3 -c \"import matplotlib.pyplot as plt; plt.hist({data}, bins={bins}); plt.title('{title}'); plt.savefig('{output}')\"",
    'chart_csv': "python3 -c \"import pandas as pd, matplotlib.pyplot as plt; df = pd.read_csv('{file}'); df.plot(x='{x}', y='{y}', kind='{kind}'); plt.savefig('{output}')\"",
    # gnuplot
    'gnuplot_line': "gnuplot -e \"set terminal png; set output '{output}'; set title '{title}'; plot '{file}' using {columns} with lines\"",
    'gnuplot_bar': "gnuplot -e \"set terminal png; set output '{output}'; set style data histogram; plot '{file}' using {column}:xtic({label_col})\"",
    # Markdown
    'md_to_html': "pandoc {input} -o {output}",
    'md_to_pdf': "pandoc {input} -o {output} --pdf-engine=xelatex",
    'md_to_docx': "pandoc {input} -o {output}",
    'md_to_pptx': "pandoc {input} -o {output}",
    'md_slides': "pandoc {input} -t revealjs -s -o {output}",
    'md_beamer': "pandoc {input} -t beamer -o {output}",
    # LaTeX
    'latex_compile': "pdflatex {input}",
    'latex_bibtex': "pdflatex {input} && bibtex {input} && pdflatex {input} && pdflatex {input}",
    'xelatex_compile': "xelatex {input}",
    'lualatex_compile': "lualatex {input}",
    # Mermaid diagrams
    'mermaid_render': "mmdc -i {input} -o {output}",
    'mermaid_svg': "mmdc -i {input} -o {output} -b transparent",
    # Graphviz
    'dot_render': "dot -Tpng {input} -o {output}",
    'dot_svg': "dot -Tsvg {input} -o {output}",
    'neato_render': "neato -Tpng {input} -o {output}",
    # PlantUML
    'plantuml_render': "plantuml {input}",
    'plantuml_svg': "plantuml -tsvg {input}",
    # Asciidoctor
    'asciidoc_html': "asciidoctor {input}",
    'asciidoc_pdf': "asciidoctor-pdf {input}",
    # HTML to PDF
    'wkhtmltopdf': "wkhtmltopdf {input} {output}",
    'weasyprint': "weasyprint {input} {output}",
    'chrome_pdf': "google-chrome --headless --print-to-pdf={output} {input}",
    # Spreadsheet
    'csv_to_xlsx': "python3 -c \"import pandas as pd; pd.read_csv('{input}').to_excel('{output}', index=False)\"",
    'xlsx_to_csv': "python3 -c \"import pandas as pd; pd.read_excel('{input}').to_csv('{output}', index=False)\"",
    'json_to_xlsx': "python3 -c \"import pandas as pd; pd.read_json('{input}').to_excel('{output}', index=False)\"",
    # Report generation
    'jupyter_execute': "jupyter nbconvert --to notebook --execute {input} --output {output}",
    'jupyter_html': "jupyter nbconvert --to html {input}",
    'jupyter_pdf': "jupyter nbconvert --to pdf {input}",
    'jupyter_slides': "jupyter nbconvert --to slides {input}",
    # Static site
    'mkdocs_build': "mkdocs build",
    'mkdocs_serve': "mkdocs serve",
    'hugo_build': "hugo",
    'hugo_serve': "hugo server -D",
    'jekyll_build': "bundle exec jekyll build",
    'jekyll_serve': "bundle exec jekyll serve",
}
