import logging
from src.config import Config
from src.application import Application
from src.utils.logging_config import setup_logging

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        config = Config.load_from_file('vulkan_app/config.yaml')
        app = Application(config)
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application shutting down")

if __name__ == "__main__":
    main()
