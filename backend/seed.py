import random
import sys
import os

# Ensure backend can be imported when running from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, engine, Base
from backend.models import Provider

# Recreate tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Pakistani names pool
FIRST_NAMES = [
    "Ali", "Ahmed", "Muhammad", "Usman", "Bilal", "Hamza", "Tariq", 
    "Imran", "Salman", "Rizwan", "Faizan", "Kamran", "Kashif", "Zain",
    "Adil", "Nadeem", "Yasir", "Fahad", "Waqas", "Shahzaib", "Danish"
]
LAST_NAMES = [
    "Khan", "Qureshi", "Ahmed", "Shah", "Baloch", "Siddiqui", 
    "Malik", "Ansari", "Rajput", "Shaikh", "Awan", "Javed", "Iqbal"
]

SKILLS = [
    "AC Mechanic", "Plumber", "Electrician", "Carpenter", 
    "Generator Mechanic", "Washing Machine Technician"
]

# Bounding box for Karachi (approximate)
KARACHI_LAT_MIN = 24.75
KARACHI_LAT_MAX = 25.00
KARACHI_LNG_MIN = 66.90
KARACHI_LNG_MAX = 67.20

# Shah Faisal Town (center bias)
SHAH_FAISAL_LAT = 24.8825
SHAH_FAISAL_LNG = 67.1444

def generate_phone(index):
    # Generating unique Pakistani phone numbers
    return f"+923{str(index).zfill(9)}"

def seed_providers(num_providers=500):
    db = SessionLocal()
    try:
        providers = []
        for i in range(1, num_providers + 1):
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            phone = generate_phone(i)
            skill = random.choice(SKILLS)
            
            # 30% chance to be tightly clustered around Shah Faisal Town, 70% broader Karachi
            if random.random() < 0.3:
                lat = SHAH_FAISAL_LAT + random.uniform(-0.02, 0.02)
                lng = SHAH_FAISAL_LNG + random.uniform(-0.02, 0.02)
            else:
                lat = random.uniform(KARACHI_LAT_MIN, KARACHI_LAT_MAX)
                lng = random.uniform(KARACHI_LNG_MIN, KARACHI_LNG_MAX)
            
            # Realistic stats distribution
            rating = round(random.uniform(2.5, 5.0), 1)
            reliability_score = random.randint(40, 100)
            base_rate_pkr = random.choice([500, 600, 800, 1000, 1200, 1500, 2000, 2500])
            cancellation_rate = round(random.uniform(0.0, 0.4), 2)
            
            # Mostly available
            is_available = random.random() < 0.85
            
            provider = Provider(
                name=name,
                phone=phone,
                skill_specialization=skill,
                lat=lat,
                lng=lng,
                rating=rating,
                reliability_score=reliability_score,
                base_rate_pkr=base_rate_pkr,
                cancellation_rate=cancellation_rate,
                is_available=is_available
            )
            providers.append(provider)
            
        db.add_all(providers)
        db.commit()
        print(f"Successfully seeded {num_providers} providers to the database.")
    except Exception as e:
        print(f"Error seeding providers: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting database seeding...")
    seed_providers(500)
