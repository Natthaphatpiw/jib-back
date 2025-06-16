import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
import openai

load_dotenv()

def test_gemini():
    print("🧪 Testing Gemini...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No Gemini API key")
        return False
    
    try:
        start_time = time.time()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = "Analyze this query: 'โน้ตบุ๊คแรงๆ งบ 25000'. Return JSON with category, price_max, performance_level."
        
        response = model.generate_content(prompt)
        end_time = time.time()
        
        print(f"✅ Gemini responded in {end_time - start_time:.2f}s")
        print(f"📝 Response: {response.text[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return False

def test_openai():
    print("\n🧪 Testing OpenAI...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OpenAI API key")
        return False
    
    try:
        start_time = time.time()
        client = openai.OpenAI(api_key=api_key)
        
        prompt = "Analyze this query: 'โน้ตบุ๊คแรงๆ งบ 25000'. Return JSON with category, price_max, performance_level."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        end_time = time.time()
        
        print(f"✅ OpenAI responded in {end_time - start_time:.2f}s")
        print(f"📝 Response: {response.choices[0].message.content[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing LLM connections...")
    
    gemini_works = test_gemini()
    openai_works = test_openai()
    
    print(f"\n📊 Results:")
    print(f"Gemini: {'✅ Working' if gemini_works else '❌ Failed'}")
    print(f"OpenAI: {'✅ Working' if openai_works else '❌ Failed'}")