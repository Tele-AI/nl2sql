"""
Configuration settings for the NL2SQL API tests.
These settings can be overridden using command line arguments when running the tests.
"""

# Default settings for API tests
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_API_TIMEOUT = 10  # Request timeout in seconds

# Test environment settings
TEST_ENV = {
    "development": {
        "host": "localhost",
        "port": 8000,
    },
    "staging": {
        "host": "staging-api.example.com",
        "port": 8000,
    },
    "production": {
        "host": "api.example.com", 
        "port": 443,
    }
}

# Test data size settings
MAX_TEST_DATA_SIZE = 100  # Maximum number of items to create in bulk tests 