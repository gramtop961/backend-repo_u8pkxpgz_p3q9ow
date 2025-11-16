import os
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="ZPHS Kuchanpally AI Buddy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TutorRequest(BaseModel):
    message: str = Field(..., description="Learner message in English")
    level: Optional[str] = Field("beginner", description="Learner level: beginner|intermediate|advanced")


class TutorResponse(BaseModel):
    reply: str
    suggestions: List[str] = []
    prompt: Optional[str] = None


COMMON_CORRECTIONS = {
    "i am": "I am",
    "i" : "I",
    "dont": "don't",
    "doesnt": "doesn't",
    "cant": "can't",
    "wont": "won't",
    "im": "I'm",
    "u": "you",
    "ur": "your",
    "r": "are",
    "there english": "their English",
    "there are": "there are",
    "they is": "they are",
    "he have": "he has",
    "she have": "she has",
    "i has": "I have",
}

END_PROMPTS = [
    "Tell me about your day in three sentences.",
    "Describe your favorite teacher and why you like them.",
    "What is your hobby? Explain it like you are teaching a friend.",
    "Make a short plan for tomorrow using future tense.",
]


def basic_improve(text: str) -> (str, List[str]):
    """Very simple, rule-based improvement for English sentences.
    It fixes casing, adds trailing punctuation, and applies a few common corrections.
    """
    original = text.strip()
    lowered = original.lower()
    suggestions: List[str] = []

    # Apply small dictionary corrections
    improved = lowered
    for wrong, right in COMMON_CORRECTIONS.items():
        if wrong in improved:
            improved = improved.replace(wrong, right)
            suggestions.append(f"Consider using '{right}' instead of '{wrong}'.")

    # Capitalize first letter if needed
    if improved:
        improved = improved[0].upper() + improved[1:]

    # Add period if sentence seems to end without punctuation
    if improved and improved[-1] not in ".?!":
        improved += "."

    # If it is a question but missing question mark
    if any(improved.lower().startswith(q) for q in ["what", "why", "how", "where", "when", "who", "which", "do ", "does ", "is ", "are ", "can ", "could ", "would "]):
        if improved.endswith("."):
            improved = improved[:-1] + "?"

    # If no changes were made, add an encouraging suggestion
    if improved == original:
        suggestions.append("Great job! Your sentence looks good. Try to add more detail.")

    return improved, suggestions


@app.get("/")
def read_root():
    return {"message": "ZPHS Kuchanpally AI Buddy Backend"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


@app.post("/api/tutor", response_model=TutorResponse)
def tutor(req: TutorRequest):
    user_text = req.message.strip()

    # If empty, encourage the learner to speak
    if not user_text:
        return TutorResponse(
            reply="I didn't hear anything. Try saying a simple sentence about your day.",
            suggestions=["Speak slowly and clearly.", "Start with: 'Today I ...'"] ,
            prompt="Say: 'Today I woke up early and ...'"
        )

    improved, tips = basic_improve(user_text)

    # Create a helpful reply depending on level
    if req.level == "beginner":
        reply = (
            f"You said: '{user_text}'. Here is a clearer version: '{improved}'. "
            "Well done! Try to use full sentences and simple tenses."
        )
    elif req.level == "advanced":
        reply = (
            f"Your idea is good. A more natural phrasing is: '{improved}'. "
            "Consider adding specific details and varied vocabulary."
        )
    else:
        reply = (
            f"Nice! You can say: '{improved}'. "
            "Keep practicing your rhythm and pronunciation."
        )

    # Pick a practice prompt
    import random
    prompt = random.choice(END_PROMPTS)

    return TutorResponse(
        reply=reply,
        suggestions=tips or ["Great effort! Add one more sentence to continue."],
        prompt=prompt,
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
