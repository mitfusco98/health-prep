from flask import jsonify, render_template_string
from app import app
from profiler import profiler
from jwt_utils import admin_required
import json


@app.route("/admin/performance", methods=["GET"])
@admin_required
def performance_dashboard():
    """Performance monitoring dashboard"""
    report = profiler.generate_report()

    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Performance Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric-card { 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 15px; 
                margin: 10px 0; 
                background: #f9f9f9; 
            }
            .high-severity { border-left: 4px solid #dc3545; }
            .medium-severity { border-left: 4px solid #ffc107; }
            .low-severity { border-left: 4px solid #28a745; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .slow { background-color: #ffebee; }
            .medium { background-color: #fff3e0; }
            .fast { background-color: #e8f5e8; }
            pre { background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Application Performance Dashboard</h1>
        
        <div class="metric-card">
            <h2>System Overview</h2>
            <p><strong>Uptime:</strong> {{ "%.1f"|format(report.uptime_hours) }} hours</p>
            <p><strong>Report Generated:</strong> {{ report.report_generated }}</p>
        </div>
        
        <div class="metric-card">
            <h2>Slowest Routes</h2>
            <table>
                <tr>
                    <th>Route</th>
                    <th>Avg Duration (ms)</th>
                    <th>Max Duration (ms)</th>
                    <th>Call Count</th>
                    <th>Status</th>
                </tr>
                {% for route in report.slowest_routes %}
                <tr class="{% if route.avg_duration_ms > 1000 %}slow{% elif route.avg_duration_ms > 500 %}medium{% else %}fast{% endif %}">
                    <td>{{ route.route }}</td>
                    <td>{{ "%.1f"|format(route.avg_duration_ms) }}</td>
                    <td>{{ "%.1f"|format(route.max_duration_ms) }}</td>
                    <td>{{ route.call_count }}</td>
                    <td>
                        {% if route.avg_duration_ms > 1000 %}🔴 Slow
                        {% elif route.avg_duration_ms > 500 %}🟡 Medium
                        {% else %}🟢 Fast{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="metric-card">
            <h2>Slowest Functions</h2>
            <table>
                <tr>
                    <th>Function</th>
                    <th>Avg Duration (ms)</th>
                    <th>Max Duration (ms)</th>
                    <th>Call Count</th>
                </tr>
                {% for func in report.slowest_functions %}
                <tr>
                    <td>{{ func.function }}</td>
                    <td>{{ "%.1f"|format(func.avg_duration_ms) }}</td>
                    <td>{{ "%.1f"|format(func.max_duration_ms) }}</td>
                    <td>{{ func.call_count }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="metric-card">
            <h2>Performance Recommendations</h2>
            {% for rec in report.recommendations %}
            <div class="metric-card {{ rec.severity }}-severity">
                <h4>{{ rec.type|title }} - {{ rec.severity|title }} Priority</h4>
                <p><strong>Issue:</strong> {{ rec.description }}</p>
                <p><strong>Suggestion:</strong> {{ rec.suggestion }}</p>
            </div>
            {% endfor %}
        </div>
        
        <div class="metric-card">
            <h2>Raw Data (JSON)</h2>
            <pre>{{ report_json }}</pre>
        </div>
        
    </body>
    </html>
    """

    return render_template_string(
        dashboard_html, report=report, report_json=json.dumps(report, indent=2)
    )


@app.route("/admin/performance/api", methods=["GET"])
@admin_required
def performance_api():
    """Get performance data as JSON"""
    return jsonify(profiler.generate_report())


@app.route("/admin/performance/recommendations", methods=["GET"])
@admin_required
def performance_recommendations():
    """Get performance recommendations"""
    return jsonify(profiler.get_recommendations())
