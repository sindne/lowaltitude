import json
import os
_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "training", "evaluation_results")
def generate_html_report():
    json_path = os.path.join(_OUTPUT_DIR, "bleu_comparison_latest.json")
    if not os.path.exists(json_path):
        print(f"[ERROR] Data file not found: {json_path}")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data_json = json.dumps(data, ensure_ascii=False)
    html = _build_html(data_json)
    output_path = os.path.join(_OUTPUT_DIR, "bleu_comprehensive_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report generated: {output_path}")
    return output_path
def _build_html(data_json: str) -> str:
    def css() -> str:
        return """
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #2196F3; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
        </style>
        """
    def js_code() -> str:
        return f"""
        <script>
            const data = {data_json};
            console.log('BLEU comparison data loaded:', data);
        </script>
        """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>BLEU Comparison Report</title>
        {css()}
    </head>
    <body>
        <div class="container">
            <h1>BLEU Score Comprehensive Comparison Report</h1>
            <div id="data-view"></div>
        </div>
        {js_code()}
    </body>
    </html>
    """
if __name__ == "__main__":
    generate_html_report()