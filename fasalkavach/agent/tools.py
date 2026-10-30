"""Tools the AI agent can call. Each tool fetches live data or runs the engine
and stores its result in a per-request `FarmSession`, so later tools can use it.

If a tool is called before what it depends on, it returns an error telling the
agent what to call first - the agent then corrects itself.
"""
from datetime import date

from data.http import FetchError
from data.location import geocode, in_punjab, reverse_geocode
from data.mandi import get_mandi_price
from data.weather import get_ensemble_forecast, get_soil_moisture
from engine.crops import CROPS, DEFAULT_COSTS, SOURCES
from engine.decision import assess, default_farm
from engine.risk import compute_event_probabilities
from engine.stage import StageError, get_crop_stage


class ToolError(Exception):
    pass


class FarmSession:
    """Holds everything learned while answering one farmer's request."""

    def __init__(self, costs: dict | None = None, today: date | None = None):
        self.today = today or date.today()
        self.costs = {**DEFAULT_COSTS, **(costs or {})}
        self.location = None
        self.crop = None
        self.stage = None
        self.forecast_meta = None
        self.risks = None
        self.soil = None
        self.price = None
        self.decision = None
        self.sources: list[dict] = []
        self.warnings: list[str] = []

    def _cite(self, what: str, source: str, fetched_at: str | None = None, stale: bool = False):
        self.sources.append({"used_for": what, "source": source,
                             "fetched_at": fetched_at, "stale": stale})
        if stale:
            self.warnings.append(f"{what}: live API failed, using cached data from {fetched_at}")

    # ---- tools ---------------------------------------------------------------

    def resolve_location(self, place_name: str | None = None, lat: float | None = None,
                         lon: float | None = None) -> dict:
        try:
            if lat is not None and lon is not None:
                if not in_punjab(lat, lon):
                    raise ToolError(f"({lat}, {lon}) is outside Punjab - this service covers Punjab only")
                loc = {"lat": lat, "lon": lon, "name": place_name or f"{lat:.3f}, {lon:.3f}"}
                try:
                    rev = reverse_geocode(lat, lon)
                    loc["district"] = rev["district"]
                    self._cite("district lookup", rev["source"], rev["fetched_at"], rev["stale"])
                except FetchError as e:
                    loc["district"] = None
                    self.warnings.append(f"District lookup failed ({e}); using Punjab-wide prices")
            elif place_name:
                g = geocode(place_name)
                loc = {k: g[k] for k in ("lat", "lon", "name", "district")}
                self._cite("location", g["source"], g["fetched_at"], g["stale"])
            else:
                raise ToolError("Give either place_name or both lat and lon")
        except FetchError as e:
            raise ToolError(str(e))
        self.location = loc
        return loc

    def get_crop_stage(self, crop: str, planted_on: str) -> dict:
        try:
            self.stage = get_crop_stage(crop, planted_on, self.today)
        except StageError as e:
            raise ToolError(str(e))
        self.crop = crop
        self._cite("crop stages & sensitivities", SOURCES[self.stage["source"]])
        return self.stage

    def get_weather_risk(self) -> dict:
        if not self.location:
            raise ToolError("Call resolve_location first")
        if not self.crop:
            raise ToolError("Call get_crop_stage first (risk thresholds depend on the crop)")
        try:
            fc = get_ensemble_forecast(self.location["lat"], self.location["lon"])
        except FetchError as e:
            raise ToolError(str(e))
        self.forecast_meta = {k: fc[k] for k in ("model", "is_ensemble", "source", "fetched_at")}
        if not fc["is_ensemble"]:
            self.warnings.append("Ensemble forecast unavailable - probabilities are 0/100% from a single run (low confidence)")
        self._cite("weather forecast", fc["source"], fc["fetched_at"], fc["stale"])
        self.risks = compute_event_probabilities(fc, self.crop)
        # Give the agent a compact view; the UI gets the full daily detail
        return {
            "forecast": self.forecast_meta,
            "events": {k: {"label": v["label"], "window_probability": v["window"],
                           "next_days": v["daily"][:7]}
                       for k, v in self.risks.items()},
        }

    def get_soil_moisture(self) -> dict:
        if not self.location:
            raise ToolError("Call resolve_location first")
        try:
            self.soil = get_soil_moisture(self.location["lat"], self.location["lon"])
        except FetchError as e:
            raise ToolError(str(e))
        self._cite("soil moisture", self.soil["source"], self.soil["fetched_at"], self.soil["stale"])
        return self.soil

    def get_mandi_price(self) -> dict:
        if not self.crop:
            raise ToolError("Call get_crop_stage first")
        district = (self.location or {}).get("district")
        self.price = get_mandi_price(self.crop, district)
        self.warnings.extend(self.price.get("warnings", []))
        self._cite("crop price", self.price["source"], self.price.get("fetched_at"),
                   self.price.get("stale", False))
        return self.price

    def evaluate_actions(self, area_acres: float, yield_q_per_acre: float | None = None) -> dict:
        missing = [n for n, v in (("get_crop_stage", self.stage), ("get_weather_risk", self.risks),
                                  ("get_mandi_price", self.price)) if v is None]
        if missing:
            raise ToolError("Call these first: " + ", ".join(missing))
        if not area_acres or area_acres <= 0:
            raise ToolError("area_acres must be a positive number")
        farm = default_farm(self.crop, area_acres, yield_q_per_acre, self.price["price_rs_per_q"])
        if not yield_q_per_acre:
            self.warnings.append(f"Yield not given - using Punjab average {farm['yield_q_per_acre']} q/acre")
        self.decision = assess(self.crop, self.stage, self.risks, farm, self.costs, self.soil)
        self.decision["farm"] = farm
        return self.decision

    def facts(self) -> dict:
        """Everything computed so far - what the advisory is allowed to mention."""
        return {"location": self.location, "stage": self.stage, "forecast": self.forecast_meta,
                "risks": self.risks, "soil": self.soil, "price": self.price,
                "decision": self.decision, "costs": self.costs}


TOOL_SCHEMAS = [
    {
        "name": "resolve_location",
        "description": "Find the farm's coordinates and district in Punjab. Pass lat+lon if the farmer "
                       "picked a point on the map, otherwise pass place_name (village, town or district).",
        "input_schema": {
            "type": "object",
            "properties": {
                "place_name": {"type": "string"},
                "lat": {"type": "number"},
                "lon": {"type": "number"},
            },
        },
    },
    {
        "name": "get_crop_stage",
        "description": "Get the current growth stage of the crop and how sensitive that stage is to each weather event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "enum": list(CROPS)},
                "planted_on": {"type": "string", "description": "Sowing (wheat) or transplanting (rice) date, YYYY-MM-DD"},
            },
            "required": ["crop", "planted_on"],
        },
    },
    {
        "name": "get_weather_risk",
        "description": "Fetch the live ensemble weather forecast for the farm and compute the probability of each "
                       "damaging event (rain, heavy rain, strong wind, heat stress, frost) per day and per window. "
                       "Requires resolve_location and get_crop_stage.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_soil_moisture",
        "description": "Fetch current topsoil moisture. Wet soil makes heavy rain more damaging (waterlogging). "
                       "Optional - if it fails, continue without it.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_mandi_price",
        "description": "Fetch today's mandi (market) price for the crop near the farm, used to value the crop in Rs.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "evaluate_actions",
        "description": "Run the cost-loss decision engine: expected loss in Rs and, for each protective action, "
                       "whether its benefit exceeds its cost. Requires get_crop_stage, get_weather_risk and get_mandi_price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "area_acres": {"type": "number"},
                "yield_q_per_acre": {"type": "number", "description": "Farmer's usual yield; omit if unknown"},
            },
            "required": ["area_acres"],
        },
    },
    {
        "name": "submit_advisory",
        "description": "Submit the final advisory for the farmer. It is checked automatically: every number must "
                       "come from tool results and recommended_action_ids must match the decision engine. "
                       "If the check fails you get the problems back - fix them and submit again.",
        "input_schema": {
            "type": "object",
            "properties": {
                "headline": {"type": "string", "description": "One short line, in the farmer's language"},
                "advisory_text": {"type": "string", "description": "3-6 short sentences in the farmer's language: what to do, when, and why"},
                "answer_to_question": {"type": "string", "description": "Direct answer to the farmer's question, if they asked one"},
                "recommended_action_ids": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string", "enum": ["en", "hi", "pa"]},
            },
            "required": ["headline", "advisory_text", "recommended_action_ids", "language"],
        },
    },
]
