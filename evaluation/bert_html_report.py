import json
import os
_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "training", "evaluation_results"
)
def generate_bert_html_report(results_path: str = None) -> str:
    if results_path is None:
        results_path = os.path.join(_OUTPUT_DIR, "bert_similarity_results.json")
    if not os.path.exists(results_path):
        alt_paths = [
            os.path.join(_OUTPUT_DIR, "bert_similarity_results.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "bert_similarity_results.json"),
        ]
        for p in alt_paths:
            if os.path.exists(p):
                results_path = p
                break
        else:
            raise FileNotFoundError(f"Results not found: {results_path}")
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data_json = json.dumps(data, ensure_ascii=False)
    html = _build_html(data_json)
    output_path = os.path.join(_OUTPUT_DIR, "bert_similarity_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"BERT HTML report generated: {output_path}")
    return output_path
def _build_html(data_json: str) -> str:
    def css() -> str:
        return """
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
        </style>
        """
    def js_code() -> str:
        return f"""
        <script>
            const data = {data_json};
            console.log('BERT similarity data loaded:', data);
        </script>
        """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>BERT Similarity Report</title>
        {css()}
    </head>
    <body>
        <div class="container">
            <h1>BERT Similarity Analysis Report</h1>
            <div id="data-view"></div>
        </div>
        {js_code()}
    </body>
    </html>
    """