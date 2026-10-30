"""Central configuration. Everything secret or deployment-specific comes from env vars."""
import os

try:  # Optional: load a local .env file during development
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- External services -------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-opus-5-5")
DATA_GOV_API_KEY = os.environ.get("DATA_GOV_API_KEY", "")

OPEN_METEO_ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
# Agmarknet "Current daily price of various commodities from various markets (Mandi)"
AGMARKNET_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# Ensemble models tried in order. ECMWF has 51 members, GFS 31.
ENSEMBLE_MODELS = ["ecmwf_ifs025", "gfs_seamless"]
FORECAST_DAYS = 10

# --- Behaviour ---------------------------------------------------------------
HTTP_TIMEOUT_S = 12
CACHE_TTL_S = 30 * 60          # weather/price responses are reused for 30 minutes
AGENT_MAX_STEPS = 10           # hard cap on LLM round-trips per request
AGENT_MAX_VALIDATION_RETRIES = 2

# Punjab bounding box (approx.) - requests outside it are rejected
PUNJAB_BOUNDS = {"lat_min": 29.5, "lat_max": 32.6, "lon_min": 73.8, "lon_max": 77.0}
