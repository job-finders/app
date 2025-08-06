from src.config import config_instance
from src.main import create_app


# Job Finders
app = create_app(config=config_instance())


# Add this to see all registered routes
@app.route('/debug/routes')
def show_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    return routes


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8084, debug=True, extra_files=['src', 'templates', 'static'])
