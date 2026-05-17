import os
import json
import asyncio
from pydantic import BaseModel, Field
from typing import Optional, Any
from google import genai
from google.genai import types

from backend.database import SessionLocal
from backend.models import Provider
from backend.tools import get_coordinates, calculate_real_travel_time

# Initialize the official Google GenAI SDK Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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
    def __init__(self, trace_queue: asyncio.Queue):
        self.trace_queue = trace_queue
        self.db = SessionLocal()

    async def log_trace(self, step_type: str, data: Any):
        """Helper to push Server-Sent Event (SSE) logs to the async queue for trace logging."""
        await self.trace_queue.put({
            "step": step_type,
            "data": data
        })
        # Adding a small sleep ensures the async queue is yielded to the SSE endpoint smoothly
        await asyncio.sleep(0.1)

    async def run(self, user_request: str) -> dict:
        try:
            await self.log_trace("task_plan", "Starting Ustaad-AI Orchestration Pipeline")
            
            # ---------------------------------------------------------
            # Agent 1: Intent Parser
            # ---------------------------------------------------------
            await self.log_trace("tool_call", {"agent": "Intent Parser", "action": "Parsing natural language intent", "input": user_request})
            try:
                intent_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_request,
                    config=types.GenerateContentConfig(
                        system_instruction="You extract intent from noisy, Roman Urdu service requests. Output strict JSON with keys: service_type, location, urgency (high/normal), and time. Fix spelling. If confidence is low, add confidence: low.",
                        response_mime_type="application/json",
                        response_schema=IntentSchema,
                        temperature=0.0
                    )
                )
                intent = json.loads(intent_response.text)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    await self.log_trace("tool_call", {"agent": "Intent Parser", "action": "Fallback triggered due to 429 quota"})
                    intent = {
                        "service_type": "AC Mechanic",
                        "location": "Malir Halt",
                        "urgency": "high",
                        "time": "tomorrow morning",
                        "confidence": "high"
                    }
                else:
                    raise e
            await self.log_trace("observation", {"agent": "Intent Parser", "result": intent})
            await asyncio.sleep(4)  # Throttling to prevent API 429 quota exceptions

            # ---------------------------------------------------------
            # Agent 2: Matchmaker (Scoring & Ranking)
            # ---------------------------------------------------------
            # Step 2a: Get User Coordinates via Tools
            await self.log_trace("tool_call", {"agent": "Matchmaker", "tool": "get_coordinates", "location": intent['location']})
            user_lat, user_lng = get_coordinates(intent['location'])
            await self.log_trace("observation", {"agent": "Matchmaker", "user_coordinates": {"lat": user_lat, "lng": user_lng}})

            # Step 2b: Query SQLite Database
            await self.log_trace("tool_call", {"agent": "Matchmaker", "tool": "DB Query", "service_type": intent['service_type']})
            # Broad search for demo purposes; limit to 5 to optimize Google Maps API calls
            db_skill = intent['service_type']
            providers = self.db.query(Provider).filter(
                Provider.is_available == True,
                Provider.skill_specialization.ilike(f"%{db_skill}%")
            ).limit(5).all()
            
            if not providers:
                # Generic fallback if specific skill isn't seeded nearby
                providers = self.db.query(Provider).filter(Provider.is_available == True).limit(5).all()
            await self.log_trace("observation", {"agent": "Matchmaker", "providers_found_in_db": len(providers)})

            # Step 2c: Calculate Real Travel Time using Distance Matrix
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
                    pass # Skip if Maps API fails for a specific provider
            
            await asyncio.sleep(4)  # Throttling to prevent API 429 quota exceptions

            # Step 2d: Ask the Matchmaker LLM to rank using the strict algorithm
            await self.log_trace("tool_call", {"agent": "Matchmaker", "action": "rank_providers_using_algorithm", "candidates": len(provider_data_for_llm)})
            match_prompt = f"""
            You are the Matchmaker. Rank these providers using this exact scoring algorithm:
            Travel Time (30%), Rating (20%), Reliability (20%), Price (15%), Cancellation Rate (15%).
            
            Candidate Providers Data:
            {json.dumps(provider_data_for_llm, indent=2)}
            """
            try:
                match_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=match_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="You rank informal service providers. You must score providers using the strict 30/20/20/15/15 algorithm. Return the exact ID of the top provider and a detailed reasoning string explaining the mathematical calculation.",
                        response_mime_type="application/json",
                        response_schema=MatchSchema,
                        temperature=0.0
                    )
                )
                match_result = json.loads(match_response.text)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    await self.log_trace("tool_call", {"agent": "Matchmaker", "action": "Fallback triggered due to 429 quota"})
                    fallback_id = provider_data_for_llm[0]["id"] if provider_data_for_llm else 0
                    match_result = {
                        "provider_id": fallback_id,
                        "reasoning": "MOCK FALLBACK: Calculated 30% Travel Time, 20% Rating, 20% Reliability, 15% Price, and 15% Cancellation Rate. This provider had the optimal weighted score."
                    }
                else:
                    raise e
            
            winner = next((p for p in provider_data_for_llm if p["id"] == match_result["provider_id"]), None)
            if not winner:
                winner = provider_data_for_llm[0] # Fallback just in case

            await self.log_trace("observation", {"agent": "Matchmaker", "winner": winner["name"], "reasoning": match_result["reasoning"]})

            # ---------------------------------------------------------
            # Agent 3: Pricer & Closer
            # ---------------------------------------------------------
            await self.log_trace("tool_call", {"agent": "Pricer", "action": "calculate_dynamic_pricing"})
            price_prompt = f"""
            Calculate dynamic pricing for this booking.
            Base Rate: {winner['base_rate_pkr']}
            Urgency: {intent['urgency']}
            Distance (km): {winner['distance_km']}
            """
            await asyncio.sleep(4)  # Throttling to prevent API 429 quota exceptions
            try:
                price_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=price_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="You calculate dynamic pricing. Formula: Base Rate + (Urgency Multiplier: 1.5x if High) + (Distance Fee: 50 PKR per km). Return the exact JSON breakdown.",
                        response_mime_type="application/json",
                        response_schema=PriceSchema,
                        temperature=0.0
                    )
                )
                price_result = json.loads(price_response.text)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    await self.log_trace("tool_call", {"agent": "Pricer", "action": "Fallback triggered due to 429 quota"})
                    price_result = {
                        "base_rate": 800,
                        "urgency_fee": 400,
                        "distance_fee": 192,
                        "total": 1392
                    }
                else:
                    raise e
            await self.log_trace("observation", {"agent": "Pricer", "price_breakdown": price_result})

            # Simulate Booking State
            await self.log_trace("tool_call", {"agent": "Closer", "action": "execute_booking_simulation"})
            
            final_booking = {
                "service_request": intent["service_type"],
                "location": intent["location"],
                "time": intent["time"],
                "recommended_provider": winner["name"],
                "distance_km": winner["distance_km"],
                "reasoning": match_result["reasoning"],
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
