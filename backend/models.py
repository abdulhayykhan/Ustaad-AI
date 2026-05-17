from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime
from backend.database import Base
from datetime import datetime

class Provider(Base):
    """
    Provider model to store information about local service workers.
    Includes the 6 key factors used by the Matchmaker Agent to rank providers.
    """
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, index=True, unique=True)
    skill_specialization = Column(String, index=True)
    
    # Location (e.g., coordinates in Shah Faisal Town)
    lat = Column(Float)
    lng = Column(Float)
    
    # Matching Factors for the Agent's algorithm
    rating = Column(Float, default=0.0)             # Rating: 0.0 - 5.0
    reliability_score = Column(Integer, default=50) # Reliability: 0 - 100
    base_rate_pkr = Column(Integer, default=500)    # Base Rate in PKR
    cancellation_rate = Column(Float, default=0.0)  # Cancellation Rate: 0.0 - 1.0
    
    # Current Status
    is_available = Column(Boolean, default=True)


class Booking(Base):
    """
    Booking model to store simulated booking states and pricing.
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, index=True)
    provider_id = Column(Integer, index=True)
    service_type = Column(String)
    
    # Status can be: pending, confirmed, completed, disputed
    status = Column(String, default="pending") 
    
    # Detailed breakdown calculated by the Pricer Agent
    price_breakdown = Column(JSON)
    
    # Time of the booking
    scheduled_time = Column(DateTime, default=datetime.utcnow)
