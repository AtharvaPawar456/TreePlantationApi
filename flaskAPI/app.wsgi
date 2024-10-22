import sys
import os

# Add the path to your application directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app as application  # Replace 'your_flask_app' with your actual Flask app module name
