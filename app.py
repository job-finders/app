from src.config import config_instance
from src.main import create_app
import threading

# Job Finders
app, junction_scrapper = create_app(config=config_instance())


def run_scrapper_scheduler():
    """

    :return:
    """
    junction_scrapper.loop.run_forever()


if __name__ == "__main__":
    scrapper_thread = threading.Thread(target=run_scrapper_scheduler, daemon=True)
    scrapper_thread.start()

    app.run(host='0.0.0.0', port=8084, debug=True, extra_files=['src', 'templates', 'static'])
