"""Hub-wide defaults."""

# Uncommon local port — avoids 3000/5173/8000/8080 dev-server collisions.
DEFAULT_PORT = 17482
DEFAULT_HOST = "127.0.0.1"
DEFAULT_LOCAL_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"