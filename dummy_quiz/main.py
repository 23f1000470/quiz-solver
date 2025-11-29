from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
import logging
from pydantic import BaseModel, Field
from typing import Optional, Any, Union

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str
    answer: Any  # Use Any instead of specific type to preserve case

app = FastAPI(title="Comprehensive Quiz Test Suite")

# Serve static files
app.mount("/static", StaticFiles(directory="dummy_quiz/static"), name="static")

logger = logging.getLogger("dummy_quiz")

BASE_URL = "http://127.0.0.1:9001"

@app.post("/submit")
async def submit_answer(request: QuizRequest, fastapi_request: Request):
    """Submit answer endpoint"""
    try:
        # Also get the raw JSON body to preserve case
        raw_body = await fastapi_request.body()
        raw_json = json.loads(raw_body)
        raw_answer = raw_json.get('answer', '')
        
        print(f"🎯 RAW BODY ANSWER: {repr(raw_answer)}")
        print(f"🎯 PYDANTIC ANSWER: {repr(request.answer)}")
        
        # Use the raw answer from the body to preserve case
        answer_to_validate = raw_answer if isinstance(raw_answer, str) else str(request.answer)
        
        print(f"🎯 FINAL ANSWER TO VALIDATE: {repr(answer_to_validate)}")
        
        # Rest of the validation logic using answer_to_validate...
        email = request.email
        secret = request.secret
        url = request.url
        
        print(f"🔔 SUBMISSION: {url} - Answer: {answer_to_validate}")
        
        # Convert answer to string for comparison to handle both "42" and 42
        answer_str = str(answer_to_validate).strip().lower() if answer_to_validate is not None else ""
        
        # Quiz answer validation logic
        correct, next_url, reason = validate_answer(url, answer_to_validate)  # Pass the raw answer
        
        response = {
            "correct": correct,
            "url": next_url,
            "reason": reason
        }
        
        print(f"📤 RESPONSE: Correct: {correct}, Next: {next_url}")
        print("=" * 50)
        return response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e), "correct": False, "url": None}


def validate_answer(url: str, answer: str) -> tuple:
    """Validate answers for different quiz types"""
    print(f"🔍 VALIDATE_ANSWER INPUT: {repr(answer)} (type: {type(answer)})")
    # Quiz 1: Simple Math
    if url == f"{BASE_URL}/quiz1":
        correct = answer == "42"
        next_url = f"{BASE_URL}/quiz2" if correct else None
        reason = "Correct! Math is fun!" if correct else f"Expected '42', got '{answer}'"
    
    # Quiz 2: CSV Sum
    elif url == f"{BASE_URL}/quiz2":
        correct = answer == "100"  # Sum of demo.csv values
        next_url = f"{BASE_URL}/quiz3" if correct else None
        reason = "Correct! CSV parsing works!" if correct else f"Expected '100', got '{answer}'"
    
    # Quiz 3: CSV Mean
    elif url == f"{BASE_URL}/quiz3":
        # Try to convert to float and compare
        try:
            answer_float = float(answer)
            correct = abs(answer_float - 80.0) < 0.001  # Allow small floating point errors
            next_url = f"{BASE_URL}/quiz4" if correct else None
            reason = "Correct! Average calculation works!" if correct else f"Expected '80', got '{answer}'"
        except:
            correct = False
            next_url = None
            reason = f"Expected a number, got '{answer}'"

    # Quiz 4: CSV Filter Sum
    elif url == f"{BASE_URL}/quiz4":
        correct = answer == "30"  # Sum of North region quantities
        next_url = f"{BASE_URL}/quiz5" if correct else None
        reason = "Correct! Filtering works!" if correct else f"Expected '30', got '{answer}'"
    
    # Quiz 5: JSON Sum
    elif url == f"{BASE_URL}/quiz5":
        correct = answer == "20"  # Sum of [3, 7, 10]
        next_url = f"{BASE_URL}/quiz6" if correct else None
        reason = "Correct! JSON parsing works!" if correct else f"Expected '20', got '{answer}'"
    
    # Quiz 6: JSON Max
    elif url == f"{BASE_URL}/quiz6":
        correct = answer == "42"  # Max of [5, 42, 17]
        next_url = f"{BASE_URL}/quiz7" if correct else None
        reason = "Correct! Max value found!" if correct else f"Expected '42', got '{answer}'"
    
    # Quiz 7: JSON Filter Average
    elif url == f"{BASE_URL}/quiz7":
        correct = answer == "30"  # Average of temps >= 25
        next_url = f"{BASE_URL}/quiz8" if correct else None
        reason = "Correct! Filtered average works!" if correct else f"Expected '30', got '{answer}'"
    
    # Quiz 8: PDF Answer Extraction
    elif url == f"{BASE_URL}/quiz8":
        correct = answer == "314"  # From demo.pdf
        next_url = f"{BASE_URL}/quiz9" if correct else None
        reason = "Correct! PDF parsing works!" if correct else f"Expected '314', got '{answer}'"
    
    # Quiz 9: PDF Result Extraction
    elif url == f"{BASE_URL}/quiz9":
        correct = answer == "256"  # From math.pdf
        next_url = f"{BASE_URL}/quiz10" if correct else None
        reason = "Correct! PDF text extraction works!" if correct else f"Expected '256', got '{answer}'"
    
    # Quiz 10: HTML Table Scraping
    elif url == f"{BASE_URL}/quiz10":
        correct = answer == "60"  # Sum of table scores
        next_url = f"{BASE_URL}/quiz11" if correct else None
        reason = "Correct! HTML table parsing works!" if correct else f"Expected '60', got '{answer}'"
    
    # Quiz 11: Text Pattern Matching
    elif url == f"{BASE_URL}/quiz11":
        correct = answer == "xyz123"
        next_url = f"{BASE_URL}/quiz12" if correct else None
        reason = "Correct! Pattern matching works!" if correct else f"Expected 'xyz123', got '{answer}'"
    
    # Quiz 12: Simple Multiplication
    elif url == f"{BASE_URL}/quiz12":
        correct = answer == "168"  # 12 * 14
        next_url = f"{BASE_URL}/quiz13" if correct else None
        reason = "Correct! Basic math works!" if correct else f"Expected '168', got '{answer}'"
    
    # Quiz 13: Expression Evaluation
    elif url == f"{BASE_URL}/quiz13":
        correct = answer == "21"  # 2*3 + 3*5
        next_url = f"{BASE_URL}/quiz14" if correct else None
        reason = "Correct! Expression evaluation works!" if correct else f"Expected '21', got '{answer}'"
    
    # Quiz 14: Reasoning - Weight
    elif url == f"{BASE_URL}/quiz14":
        correct = answer == "same"
        next_url = f"{BASE_URL}/quiz15" if correct else None
        reason = "Correct! Reasoning works!" if correct else f"Expected 'same', got '{answer}'"
    
    # Quiz 15: Reasoning - Age
    elif url == f"{BASE_URL}/quiz15":
        correct = answer == "b"
        next_url = f"{BASE_URL}/quiz16" if correct else None
        reason = "Correct! Age reasoning works!" if correct else f"Expected 'b', got '{answer}'"
    
    # Quiz 16: General Knowledge - Capital
    elif url == f"{BASE_URL}/quiz16":
        correct = answer == "paris"
        next_url = f"{BASE_URL}/quiz17" if correct else None
        reason = "Correct! GK works!" if correct else f"Expected 'paris', got '{answer}'"
    
    # Quiz 17: General Knowledge - Ocean
    elif url == f"{BASE_URL}/quiz17":
        correct = answer == "pacific ocean"
        next_url = f"{BASE_URL}/quiz18" if correct else None
        reason = "Correct! Geography knowledge works!" if correct else f"Expected 'pacific ocean', got '{answer}'"
    
    # Quiz 18: Pattern Recognition
    elif url == f"{BASE_URL}/quiz18":
        correct = answer == "32"  # Powers of 2
        next_url = f"{BASE_URL}/quiz19" if correct else None
        reason = "Correct! Pattern recognition works!" if correct else f"Expected '32', got '{answer}'"
    
    # Quiz 19: Prime Number Check
    elif url == f"{BASE_URL}/quiz19":
        # Accept both "yes" and "1" for true, but the question expects "yes"
        answer_lower = answer.lower()
        correct = answer_lower == "yes"  # Only accept "yes"
        next_url = f"{BASE_URL}/quiz20" if correct else None
        reason = "Correct! Prime check works!" if correct else f"Expected 'yes', got '{answer}'"
    
    # Quiz 20: Final Question
    elif url == f"{BASE_URL}/quiz20":
        correct = answer == "42"
        next_url = None  # End of quiz chain
        reason = "🎉 Congratulations! All quizzes completed!" if correct else f"Expected '42', got '{answer}'"

    # In validate_answer function:
    elif url == f"{BASE_URL}/quiz-excel":
        correct = answer == "250"  # 100 + 150 = 250
        next_url = None
        reason = "Correct! Excel processing works!" if correct else f"Expected '250', got '{answer}'"
    

    # In validate_answer for quiz-base64:
    elif url == f"{BASE_URL}/quiz-base64":
        # Use the raw answer directly
        answer_str = answer if isinstance(answer, str) else str(answer)
        print(f"🔍 BASE64 VALIDATION - RAW: {repr(answer_str)}")
        
        try:
            import base64
            clean = answer_str.strip()
            print(f"🔍 CLEANED: {repr(clean)}")
            
            # Try direct decode
            decoded = base64.b64decode(clean).decode('utf-8')
            print(f"🔍 DECODED: {repr(decoded)}")
            correct = "hello world" in decoded.lower()
            print(f"🔍 CONTAINS 'hello world': {correct}")
            
        except Exception as e:
            print(f"🔍 DECODING ERROR: {e}")
            correct = False
        
        next_url = None
        reason = "Correct! Base64 file handling works!" if correct else "Expected base64 encoded 'Hello World'"
        return correct, next_url, reason

    # In validate_answer function:
    elif url == f"{BASE_URL}/quiz-api-headers":
        correct = answer == "789"  # From the protected API
        next_url = None
        reason = "Correct! API header handling works!" if correct else f"Expected '789', got '{answer}'"

    else:
        correct = False
        next_url = None
        reason = f"Unknown quiz URL: {url}"
    
    return correct, next_url, reason

# Quiz endpoints
@app.get("/")
async def root():
    return {"message": "Comprehensive Quiz Test Suite", "start_url": f"{BASE_URL}/quiz1"}

@app.get("/demo")
async def demo_quiz():
    """Simple demo quiz"""
    html = f"""
    <html><body>
        <h1>Demo Quiz</h1>
        <p>Q1. What is 15 + 27?</p>
        <p>Submit your answer to: {BASE_URL}/submit</p>
        <script>document.write('<p>JS: 15+27 = ' + (15+27) + '</p>')</script>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz1")
async def quiz1():
    """Simple Math"""
    html = f"""
    <html><body>
        <h1>Quiz 1: Simple Math</h1>
        <p>What is 15 + 27?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz2")
async def quiz2():
    """CSV Sum"""
    html = f"""
    <html><body>
        <h1>Quiz 2: CSV Sum</h1>
        <p>Download <a href="{BASE_URL}/static/demo.csv">demo.csv</a></p>
        <p>What is the sum of the 'value' column?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz3")
async def quiz3():
    """CSV Mean"""
    html = f"""
    <html><body>
        <h1>Quiz 3: CSV Mean</h1>
        <p>Download <a href="{BASE_URL}/static/prices.csv">prices.csv</a></p>
        <p>What is the mean of the 'price' column?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

# Add these additional quiz endpoints after quiz3

@app.get("/quiz4")
async def quiz4():
    """CSV Filter Sum"""
    html = f"""
    <html><body>
        <h1>Quiz 4: CSV Filter Sum</h1>
        <p>Download <a href="{BASE_URL}/static/sales.csv">sales.csv</a></p>
        <p>What is the total 'quantity' for rows where region == 'North'?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz5")
async def quiz5():
    """JSON Sum"""
    html = f"""
    <html><body>
        <h1>Quiz 5: JSON Sum</h1>
        <p>Fetch JSON from: <a href="{BASE_URL}/json-data-1">{BASE_URL}/json-data-1</a></p>
        <p>What is the sum of all numbers in the 'values' array?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz6")
async def quiz6():
    """JSON Max"""
    html = f"""
    <html><body>
        <h1>Quiz 6: JSON Max</h1>
        <p>Fetch JSON from: <a href="{BASE_URL}/json-data-2">{BASE_URL}/json-data-2</a></p>
        <p>What is the maximum value in the 'values' array?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz7")
async def quiz7():
    """JSON Filter Average"""
    html = f"""
    <html><body>
        <h1>Quiz 7: JSON Filter Average</h1>
        <p>Fetch JSON from: <a href="{BASE_URL}/json-data-3">{BASE_URL}/json-data-3</a></p>
        <p>What is the average 'temp' for cities with temp >= 25? (round to integer)</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz8")
async def quiz8():
    """PDF Answer Extraction"""
    html = f"""
    <html><body>
        <h1>Quiz 8: PDF Answer Extraction</h1>
        <p>Download <a href="{BASE_URL}/static/demo.pdf">demo.pdf</a></p>
        <p>Find the number after the word 'Answer:' in the PDF</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz9")
async def quiz9():
    """PDF Result Extraction"""
    html = f"""
    <html><body>
        <h1>Quiz 9: PDF Result Extraction</h1>
        <p>Download <a href="{BASE_URL}/static/math.pdf">math.pdf</a></p>
        <p>Find the number after 'Result =' in the PDF</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz10")
async def quiz10():
    """HTML Table Scraping"""
    html = f"""
    <html><body>
        <h1>Quiz 10: HTML Table Scraping</h1>
        <p>Visit: <a href="{BASE_URL}/table-page">{BASE_URL}/table-page</a></p>
        <p>What is the sum of all values in the 'Score' column?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz11")
async def quiz11():
    """Text Pattern Matching"""
    html = f"""
    <html><body>
        <h1>Quiz 11: Text Pattern Matching</h1>
        <p>Visit: <a href="{BASE_URL}/secret-page">{BASE_URL}/secret-page</a></p>
        <p>Find the secret code in the text and submit it exactly</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz12")
async def quiz12():
    """Simple Multiplication"""
    html = f"""
    <html><body>
        <h1>Quiz 12: Simple Multiplication</h1>
        <p>What is 12 * 14?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz13")
async def quiz13():
    """Expression Evaluation"""
    html = f"""
    <html><body>
        <h1>Quiz 13: Expression Evaluation</h1>
        <p>Let x = 3 and y = 5. Compute 2*x + 3*y</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz14")
async def quiz14():
    """Reasoning - Weight"""
    html = f"""
    <html><body>
        <h1>Quiz 14: Reasoning - Weight</h1>
        <p>Which is heavier: 1 kg of cotton or 1 kg of iron?</p>
        <p>Answer with 'same'</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz15")
async def quiz15():
    """Reasoning - Age"""
    html = f"""
    <html><body>
        <h1>Quiz 15: Reasoning - Age</h1>
        <p>Person A was born in 2000 and Person B in 1998. Who is older?</p>
        <p>Answer with 'B'</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz16")
async def quiz16():
    """General Knowledge - Capital"""
    html = f"""
    <html><body>
        <h1>Quiz 16: General Knowledge - Capital</h1>
        <p>What is the capital city of France?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz17")
async def quiz17():
    """General Knowledge - Ocean"""
    html = f"""
    <html><body>
        <h1>Quiz 17: General Knowledge - Ocean</h1>
        <p>What is the largest ocean on Earth?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz18")
async def quiz18():
    """Pattern Recognition"""
    html = f"""
    <html><body>
        <h1>Quiz 18: Pattern Recognition</h1>
        <p>Sequence: 2, 4, 8, 16, ? What is the next number?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz19")
async def quiz19():
    """Prime Number Check"""
    html = f"""
    <html><body>
        <h1>Quiz 19: Prime Number Check</h1>
        <p>Is 97 a prime number? Answer with 'yes' or 'no'</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz20")
async def quiz20():
    """Final Question"""
    html = f"""
    <html><body>
        <h1>Quiz 20: Final Question</h1>
        <p>Answer 42</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz-excel")
async def quiz_excel():
    """Excel Processing Test"""
    html = f"""
    <html><body>
        <h1>Quiz: Excel Processing</h1>
        <p>Download <a href="{BASE_URL}/static/sample.xlsx">sample.xlsx</a></p>
        <p>What is the total sales in the North region?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz-base64")
async def quiz_base64():
    """Base64 File Answer Test"""
    html = f"""
    <html><body>
        <h1>Quiz: Base64 File Answer</h1>
        <p>Generate a text file containing 'Hello World' and submit it as base64.</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/quiz-api-headers")
async def quiz_api_headers():
    """API Header Test"""
    html = f"""
    <html><body>
        <h1>Quiz: API Headers</h1>
        <p>Fetch data from: <a href="{BASE_URL}/api-protected-data">{BASE_URL}/api-protected-data</a></p>
        <p>Use Authorization: Bearer secret-token-123</p>
        <p>What is the value of the 'secret_number' field?</p>
        <p>Submit to: {BASE_URL}/submit</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/api-protected-data")
async def api_protected_data(authorization: str = Header(None)):
    """Protected API endpoint that requires headers"""
    if authorization != "Bearer secret-token-123":
        return {"error": "Unauthorized - missing or invalid Authorization header"}
    
    return {"secret_number": 789, "message": "Access granted"}

# JSON data endpoints
@app.get("/json-data-1")
async def json_data_1():
    return {"values": [3, 7, 10]}  # Sum: 20

@app.get("/json-data-2")
async def json_data_2():
    return {"values": [5, 42, 17]}  # Max: 42

@app.get("/json-data-3")
async def json_data_3():
    return {
        "cities": [
            {"name": "Chennai", "temp": 32},
            {"name": "Delhi", "temp": 28},
            {"name": "London", "temp": 18},
        ]
    }  # Average of >=25: (32+28)/2 = 30

@app.get("/table-page")
async def table_page():
    html = """
    <html><body>
        <h1>Scores Table</h1>
        <table border="1">
            <tr><th>Name</th><th>Score</th></tr>
            <tr><td>Alice</td><td>10</td></tr>
            <tr><td>Bob</td><td>20</td></tr>
            <tr><td>Charlie</td><td>30</td></tr>
        </table>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/secret-page")
async def secret_page():
    html = """
    <html><body>
        <p>Some random text here.</p>
        <p>The secret code is XYZ123 in this sentence.</p>
    </body></html>
    """
    return HTMLResponse(html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)