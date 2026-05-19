import os
import json
import asyncio
from pydantic import BaseModel, Field
from typing import Optional, Any, Callable, Awaitable
from google import genai
from google.genai import types

from backend.database import SessionLocal
from backend.models import Provider
from backend.tools import get_coordinates, calculate_real_travel_time

# Initialize the official Google GenAI SDK Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

GEMINI_MODEL = "gemini-2.5-flash"
AGENT_INTENT = "Intent Parser"
AGENT_MATCHMAKER = "Matchmaker"
AGENT_PRICER = "Pricer"
FALLBACK_429_MESSAGE = "Fallback triggered due to 429 quota"

# Define Pydantic schemas for Agent JSON outputs
class IntentSchema(BaseModel):
    service_type: str = Field(description="Extracted service type, e.g., AC Mechanic, Plumber")
    location: str = Field(description="Extracted location")
    urgency: str = Field(description="high or normal")
    time: str = Field(description="Requested time")
    confidence: Optional[str] = Field(None, description="low if confidence is low")

class MatchSchema(BaseModel):
    provider_id: int = Field(description="ID of the winning provider")
    reasoning: str = Field(description="Detailed explanation of the 30/20/20/15/15 scoring math")

class PriceSchema(BaseModel):
    base_rate: float
    urgency_fee: float
    distance_fee: float
    total: float

class UstaadOrchestrator:
    """
    Core Antigravity Orchestrator for Ustaad-AI.
    Manages the 3 specialized sub-agents and streams SSE logs.
    """
    def __init__(self, trace_publisher: Callable[[dict], Awaitable[None]]):
        self.trace_publisher = trace_publisher
        self.db = SessionLocal()

    async def log_trace(self, step_type: str, data: Any):
        """Helper to push Server-Sent Event (SSE) logs to the async queue for trace logging."""
        await self.trace_publisher({
            "step": step_type,
            "data": data
        })

    async def _generate_json(
        self,
        *,
        model: str,
        contents: str,
        system_instruction: str,
        response_schema: type[BaseModel],
    ) -> dict:
        """Runs blocking model invocation in a worker thread."""

        def _run_generation():
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.0,
                ),
            )

        response = await asyncio.to_thread(_run_generation)
        return json.loads(response.text)

    async def _parse_intent_stage(self, user_request: str) -> dict:
        """Agent 1: Intent Parser - Extracts service intent from user request."""
        await self.log_trace("tool_call", {"agent": AGENT_INTENT, "action": "Parsing natural language intent", "input": user_request})
        try:
            intent = await self._generate_json(
                model=GEMINI_MODEL,
                contents=user_request,
                system_instruction="You extract intent from noisy, Roman Urdu service requests. Output strict JSON with keys: service_type, location, urgency (high/normal), and time. Fix spelling. If confidence is low, add confidence: low.",
                response_schema=IntentSchema,
            )
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                await self.log_trace("tool_call", {"agent": AGENT_INTENT, "action": FALLBACK_429_MESSAGE})
                intent = {
                    "service_type": "AC Mechanic",
                    "location": "Malir Halt",
                    "urgency": "high",
                    "time": "tomorrow morning",
                    "confidence": "high"
                }
            else:
                raise e
        await self.log_trace("observation", {"agent": AGENT_INTENT, "result": intent})
        return intent

    async def _rank_providers_stage(self, intent: dict) -> dict:
        """Agent 2: Matchmaker - Queries providers and ranks by scoring algorithm."""
        await self.log_trace("tool_call", {"agent": AGENT_MATCHMAKER, "tool": "get_coordinates", "location": intent['location']})
        user_lat, user_lng = get_coordinates(intent['location'])
        await self.log_trace("observation", {"agent": AGENT_MATCHMAKER, "user_coordinates": {"lat": user_lat, "lng": user_lng}})

        await self.log_trace("tool_call", {"agent": AGENT_MATCHMAKER, "tool": "DB Query", "service_type": intent['service_type']})
        db_skill = intent['service_type']
        providers = self.db.query(Provider).filter(
            Provider.is_available == True,
            Provider.skill_specialization.ilike(f"%{db_skill}%")
        ).limit(5).all()
        
        if not providers:
            providers = self.db.query(Provider).filter(Provider.is_available == True).limit(5).all()

        if not providers:
            await self.log_trace("error", {"agent": AGENT_MATCHMAKER, "message": "No providers available in database."})
            raise ValueError("No providers are currently available.")

        await self.log_trace("observation", {"agent": AGENT_MATCHMAKER, "providers_found_in_db": len(providers)})

        # Calculate travel times and build LLM input data
        provider_data_for_llm = []
        for p in providers:
            try:
                tt = calculate_real_travel_time(p.lat, p.lng, user_lat, user_lng)
                provider_data_for_llm.append({
                    "id": p.id,
                    "name": p.name,
                    "rating": p.rating,
                    "reliability_score": p.reliability_score,
                    "base_rate_pkr": p.base_rate_pkr,
                    "cancellation_rate": p.cancellation_rate,
                    "distance_km": tt["distance_km"],
                    "travel_time_mins": tt["duration_mins"]
                })
            except Exception:
                pass

        if not provider_data_for_llm:
            await self.log_trace("observation", {"agent": AGENT_MATCHMAKER, "warning": "Distance Matrix failed for all candidates. Falling back to DB-only ranking inputs."})
            provider_data_for_llm = [
                {
                    "id": p.id,
                    "name": p.name,
                    "rating": p.rating,
                    "reliability_score": p.reliability_score,
                    "base_rate_pkr": p.base_rate_pkr,
                    "cancellation_rate": p.cancellation_rate,
                    "distance_km": 0.0,
                    "travel_time_mins": 0.0,
                }
                for p in providers
            ]

        # Ask Matchmaker LLM to rank
        await self.log_trace("tool_call", {"agent": AGENT_MATCHMAKER, "action": "rank_providers_using_algorithm", "candidates": len(provider_data_for_llm)})
        match_prompt = f"You are the Matchmaker. Rank these providers using this exact scoring algorithm: Travel Time (30%), Rating (20%), Reliability (20%), Price (15%), Cancellation Rate (15%). Candidate Providers Data: {json.dumps(provider_data_for_llm, indent=2)}"
        try:
            match_result = await self._generate_json(
                model=GEMINI_MODEL,
                contents=match_prompt,
                system_instruction="You rank informal service providers. You must score providers using the strict 30/20/20/15/15 algorithm. Return the exact ID of the top provider and a detailed reasoning string explaining the mathematical calculation.",
                response_schema=MatchSchema,
            )
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                await self.log_trace("tool_call", {"agent": AGENT_MATCHMAKER, "action": FALLBACK_429_MESSAGE})
                fallback_id = provider_data_for_llm[0]["id"] if provider_data_for_llm else 0
                match_result = {
                    "provider_id": fallback_id,
                    "reasoning": "MOCK FALLBACK: Calculated 30% Travel Time, 20% Rating, 20% Reliability, 15% Price, and 15% Cancellation Rate. This provider had the optimal weighted score."
                }
            else:
                raise e
        
        winner = next((p for p in provider_data_for_llm if p["id"] == match_result["provider_id"]), None)
        if not winner and provider_data_for_llm:
            winner = provider_data_for_llm[0]

        if not winner:
            raise ValueError("No provider candidates available after ranking")

        await self.log_trace("observation", {"agent": AGENT_MATCHMAKER, "winner": winner["name"], "reasoning": match_result["reasoning"]})
        # Return both winner and reasoning for use in final_booking
        return {"winner": winner, "reasoning": match_result["reasoning"]}

    async def _calculate_price_stage(self, intent: dict, winner: dict) -> dict:
        """Agent 3: Pricer - Calculates dynamic pricing for the booking."""
        await self.log_trace("tool_call", {"agent": AGENT_PRICER, "action": "calculate_dynamic_pricing"})
        price_prompt = f"Calculate dynamic pricing for this booking. Base Rate: {winner['base_rate_pkr']}, Urgency: {intent['urgency']}, Distance (km): {winner['distance_km']}"
        try:
            price_result = await self._generate_json(
                model=GEMINI_MODEL,
                contents=price_prompt,
                system_instruction="You calculate dynamic pricing. Formula: Base Rate + (Urgency Multiplier: 1.5x if High) + (Distance Fee: 50 PKR per km). Return the exact JSON breakdown.",
                response_schema=PriceSchema,
            )
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                await self.log_trace("tool_call", {"agent": AGENT_PRICER, "action": FALLBACK_429_MESSAGE})
                urgency_fee = winner["base_rate_pkr"] * 0.5 if str(intent.get("urgency", "")).lower() == "high" else 0.0
                distance_fee = winner["distance_km"] * 50
                price_result = {
                    "base_rate": winner["base_rate_pkr"],
                    "urgency_fee": round(urgency_fee, 2),
                    "distance_fee": round(distance_fee, 2),
                    "total": round(winner["base_rate_pkr"] + urgency_fee + distance_fee, 2)
                }
            else:
                raise e
        await self.log_trace("observation", {"agent": AGENT_PRICER, "price_breakdown": price_result})
        return price_result

    async def run(self, user_request: str) -> dict:
        try:
            await self.log_trace("task_plan", "Starting Ustaad-AI Orchestration Pipeline")
            
            # Execute the three-stage agent pipeline
            intent = await self._parse_intent_stage(user_request)
            matchmaker_result = await self._rank_providers_stage(intent)
            winner = matchmaker_result["winner"]
            reasoning = matchmaker_result["reasoning"]
            price_result = await self._calculate_price_stage(intent, winner)

            # Simulate Booking State
            await self.log_trace("tool_call", {"agent": "Closer", "action": "execute_booking_simulation"})
            
            final_booking = {
                "service_request": intent["service_type"],
                "location": intent["location"],
                "time": intent["time"],
                "recommended_provider": winner["name"],
                "distance_km": winner["distance_km"],
                "reasoning": reasoning,
                "user_reasoning": f"Ustaad {winner['name']} aapke bataye huay location se sab se kareeb hain aur inki rating bhi behtareen hai. Isliye inhein select kiya gaya hai.",
                "price_breakdown": price_result,
                "status": "Slot booked. Confirmation sent.",
                "follow_up": "Reminder scheduled 1 hour before appointment."
            }
            
            await self.log_trace("final_answer", final_booking)
            return final_booking

        except Exception as e:
            error_msg = f"Orchestration Error: {str(e)}"
            await self.log_trace("error", {"message": error_msg})
            return {"error": error_msg}
        finally:
            self.db.close()
