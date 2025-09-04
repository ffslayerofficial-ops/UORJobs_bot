import os
import json
import google.generativeai as genai

# Configure the Gemini API client
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None

def parse_query_with_ai(query: str) -> dict:
    """
    Uses Gemini to parse a natural language query into a structured job search dictionary.
    """
    if not model:
        raise ConnectionError("Gemini model is not configured. Check API key.")

    # This is the "prompt". We are telling the AI exactly what to do.
    prompt = f"""
    You are an expert job search query parser. Your task is to extract structured information from a user's natural language query.
    The output MUST be a valid JSON object with the following keys: "keywords", "location", and "job_type".

    Rules:
    - "keywords": The main job title or skill the user is looking for. Be specific.
    - "location": The city or area. If no location is mentioned, or if the user says "work from home" or "wfh", set this to "remote".
    - "job_type": The type of employment. Can be "full-time", "part-time", "internship", or "any". If not specified, default to "any".

    User Query: "{query}"

    JSON Output:
    """

    try:
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's valid JSON
        json_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        parsed_json = json.loads(json_response_text)
        
        # Ensure all keys are present
        parsed_json.setdefault("keywords", "any")
        parsed_json.setdefault("location", "remote")
        parsed_json.setdefault("job_type", "any")
        
        return parsed_json
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"AI parsing failed: {e}")
        # Fallback to a simple keyword extraction if AI fails
        return {"keywords": query, "location": "remote", "job_type": "any"}