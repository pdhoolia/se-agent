# In your main script or __init__.py
import logging

# Create or get the logger
logger = logging.getLogger("se-agent")
logger.setLevel(logging.DEBUG)  # Set the desired logging level

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Set the handler's level

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)