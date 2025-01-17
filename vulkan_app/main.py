import logging
from src.config import Config
from src.application import Application

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        config = Config.load_from_file('config.yaml')
        app = Application(config)
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application shutting down")

if __name__ == "__main__":
    main()
