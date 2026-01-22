import sys
import os

# Mock streamlit to avoid errors during import if not running via streamlit run
from unittest.mock import MagicMock
sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit.components.v1"] = MagicMock()

try:
    import constants
    import utils
    import database
    import auth
    import services
    import views
    # Main might trigger page config, so we import it last
    import main
    print("SUCCESS: All modules imported without error.")
except ImportError as e:
    print(f"FAIL: Import Error: {e}")
except Exception as e:
    print(f"FAIL: General Error: {e}")
