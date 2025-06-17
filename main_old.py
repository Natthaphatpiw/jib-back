import json
import os
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import openai
import google.generativeai as genai
import re
from pymongo import MongoClient

load_dotenv()

app = FastAPI(title="JIB Computer Shop AI Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Product(BaseModel):
    id: str
    brand: str
    category: str
    detail: str
    discount: int
    image: str
    link: str
    name: str
    price: int
    sellprice: int
    sku: str
    views: int
    warranty: str
    
    model_config = {"populate_by_name": True}

class SearchRequest(BaseModel):
    query: str
    llm_provider: Literal["gemini", "openai"] = "openai"

class SearchResponse(BaseModel):
    products: List[Product]
    explanation: str
    total_found: int

class FilterRequest(BaseModel):
    query: str

class FilterResponse(BaseModel):
    mongodb_filter: dict
    explanation: str

# MongoDB connection setup
def get_mongodb_connection():
    """Setup MongoDB connection"""
    try:
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://admin_KLwIX:KfFGVTJafRQD6_fmu6mjofO40Y@152.42.202.84:27017,152.42.202.84:27018,152.42.202.84:27019/dashboard-scrape-dev?replicaSet=rs0&authSource=admin&authMechanism=SCRAM-SHA-1")
        client = MongoClient(mongodb_uri)
        db = client["dashboard-scrape-dev"]
        return db
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return None

# MongoDB operations
def get_products_by_filter(mongodb_filter: dict, limit: int = 50):
    """Get products from MongoDB using filter"""
    try:
        db = get_mongodb_connection()
        if db is None:
            return []
        
        collection = db.productjibscrapes
        products = list(collection.find(mongodb_filter).limit(limit))
        
        # Convert MongoDB documents to the expected format
        for product in products:
            if '_id' in product:
                product['id'] = str(product['_id'])
                del product['_id']
        
        print(f"✅ Found {len(products)} products matching filter")
        return products
    except Exception as e:
        print(f"Error querying products from MongoDB: {e}")
        return []

# Available categories for reference
AVAILABLE_CATEGORIES = [
    "APPLE PRODUCTS", "กล้อง / กล้องวงจรปิด", "คอนเทนต์ ครีเอเตอร์", "คอมพิวเตอร์ฮาร์ดแวร์",
    "คอมพิวเตอร์เซ็ต", "คีย์บอร์ด / เมาส์ / เมาส์ปากกา", "จอคอมพิวเตอร์", "ชุดระบายความร้อน",
    "ทีวี", "ระบบขายหน้าร้าน", "ลำโพง / หูฟัง", "สมาร์ทโฟน และแท็บเล็ต", "สินค้าสำหรับองค์กร",
    "อุปกรณ์ขุดเหรียญคริปโต", "อุปกรณ์ตกแต่งเคส", "อุปกรณ์สำนักงาน", "อุปกรณ์เกมมิ่งเกียร์",
    "อุปกรณ์เน็ตเวิร์ค", "อุปกรณ์เสริม", "เครื่องพิมพ์ หมึก ดรัม และสแกนเนอร์", "เครื่องสำรองไฟ",
    "เครื่องใช้ไฟฟ้าภายในบ้าน", "เซิร์ฟเวอร์", "เดสก์ท็อป / ออลอินวัน / มินิพีซี",
    "เมมโมรี่การ์ด / ฮาร์ดดิสก์", "เว็บแคม / อุปกรณ์สำหรับการประชุม", "โดรน", "โน้ตบุ๊ค",
    "โปรเจคเตอร์", "โปรแกรมคอมพิวเตอร์", "ไลฟ์สไตล์ & แก็ดเจ็ต"
]

# Initialize AI clients
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_price_from_string(price_str: str) -> float:
    """Extract numeric price from Thai price string"""
    price_numbers = re.findall(r'[\d,]+', price_str.replace(',', ''))
    return float(price_numbers[0]) if price_numbers else 0

def analyze_query_with_ai(query: str, provider: str) -> dict:
    """Use AI to analyze user query and extract search criteria"""
    prompt = f"""
    Analyze this Thai computer shop search query and extract precise search criteria.
    Query: "{query}"
    
    AVAILABLE CATEGORIES (ใช้ตรงตามนี้เท่านั้น):
    - NOTEBOOK (โน้ตบุ๊ค, notebook)
    - CPU (ซีพียู, processor)
    - COMPUTER (คอม, desktop, คอมพิวเตอร์)
    - COMPUTERSET (คอมเซ็ต, ชุดคอม)
    - Apple (แอปเปิล, mac, iphone, ipad)
    
    ANALYSIS RULES:
    1. CATEGORY DETECTION (สำคัญมาก):
       - CPU/ซีพียู/processor → "CPU"
       - โน้ตบุ๊ค/notebook → "NOTEBOOK"
       - คอม/desktop/คอมพิวเตอร์ → "COMPUTER"
       - คอมเซ็ต/ชุดคอม → "COMPUTERSET"
       - แอปเปิล/mac/iphone/ipad → "Apple"
    
    2. PRICE ANALYSIS:
       - งบ X / ราคา X / ไม่เกิน X → price_max: X
       - ราคา X-Y → price_min: X, price_max: Y
       - ต่ำกว่า X → price_max: X-1
       - มากกว่า X → price_min: X+1
    
    3. BRAND DETECTION:
       - AMD, Intel, ASUS, HP, DELL, LENOVO, MSI, ACER, Apple, Samsung
    
    4. PERFORMANCE KEYWORDS:
       - แรงๆ/gaming/เกม/RTX/GTX → performance_level: "gaming"
       - ทำงาน/office/ออฟฟิศ → performance_level: "office"
       - แนะนำ/recommend → performance_level: "recommended"
    
    5. IMPORTANT: ตรวจสอบ category ให้แม่นยำ หาก query พูดถึง "CPU" ต้องระบุ category เป็น "CPU" 
    
    EXAMPLES:
    - "CPU แนะนำราคาไม่เกิน 20000" → {{"category": "CPU", "price_max": 20000, "performance_level": "recommended"}}
    - "โน้ตบุ๊คแรงๆ งบ 25000" → {{"category": "NOTEBOOK", "price_max": 25000, "performance_level": "gaming"}}
    - "Intel CPU ราคา 5000-10000" → {{"category": "CPU", "brands": ["Intel"], "price_min": 5000, "price_max": 10000}}
    - "ASUS notebook" → {{"category": "NOTEBOOK", "brands": ["ASUS"]}}
    
    Return ONLY valid JSON:
    {{
        "category": "exact category name or null",
        "price_min": number or null,
        "price_max": number or null,
        "keywords": ["extracted keywords"],
        "brands": ["brand names"],
        "performance_level": "gaming/office/recommended or null"
    }}
    """
    
    try:
        print(f"🤖 Starting AI analysis with {provider} for query: {query}")
        
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("❌ OpenAI API key not found, using fallback")
                return fallback_analysis(query)
                
            print("📡 Calling OpenAI API...")
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result = response.choices[0].message.content
            print(f"✅ OpenAI response: {result[:200]}...")
            
        else:  # gemini
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("❌ Gemini API key not found, using fallback")
                return fallback_analysis(query)
                
            print("📡 Calling Gemini API...")
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            result = response.text
            print(f"✅ Gemini response: {result[:200]}...")
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
            print(f"🎯 AI analysis result: {analysis}")
            # Add fallback analysis
            enhanced = enhance_analysis_with_fallback(query, analysis)
            print(f"🔧 Enhanced analysis: {enhanced}")
            return enhanced
        else:
            print("⚠️ No JSON found in AI response, using fallback")
            return fallback_analysis(query)
            
    except Exception as e:
        print(f"❌ AI analysis error: {e}")
        print("🔄 Falling back to regex analysis")
        return fallback_analysis(query)

def fallback_analysis(query: str) -> dict:
    """Fallback analysis when AI fails"""
    print(f"🔧 Using fallback analysis for query: {query}")
    analysis = {
        "category": None,
        "price_min": None,
        "price_max": None,
        "keywords": [],
        "brands": [],
        "performance_level": None
    }
    
    query_lower = query.lower()
    
    # Category detection (updated for new categories)
    if any(word in query_lower for word in ['cpu', 'ซีพียู', 'processor']):
        analysis["category"] = "CPU"
    elif any(word in query_lower for word in ['โน้ตบุ๊ค', 'notebook']):
        analysis["category"] = "NOTEBOOK"
    elif any(word in query_lower for word in ['desktop', 'คอม', 'คอมพิวเตอร์']):
        analysis["category"] = "COMPUTER"
    elif any(word in query_lower for word in ['คอมเซ็ต', 'ชุดคอม', 'computerset']):
        analysis["category"] = "COMPUTERSET"
    elif any(word in query_lower for word in ['apple', 'แอปเปิล', 'mac', 'iphone', 'ipad']):
        analysis["category"] = "Apple"
    
    # Price extraction with better regex
    price_patterns = [
        r'งบ\s*(\d+)',  # งบ 25000
        r'ราคา\s*(\d+)',  # ราคา 25000
        r'ไม่เกิน\s*(\d+)',  # ไม่เกิน 25000
        r'(\d{4,6})\s*บาท',  # 25000 บาท (4-6 digits)
        r'(\d{4,6})',  # Any 4-6 digit number (likely price)
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, query)
        if match:
            price_str = match.group(1).replace(',', '')
            analysis["price_max"] = int(price_str)
            break
    
    # Performance level
    if any(word in query_lower for word in ['แรงๆ', 'แรง', 'gaming', 'เกม']):
        analysis["performance_level"] = "gaming"
    elif any(word in query_lower for word in ['ทำงาน', 'office', 'ออฟฟิศ']):
        analysis["performance_level"] = "entry"
    
    # Brand detection
    brands = ['asus', 'acer', 'hp', 'dell', 'lenovo', 'msi']
    for brand in brands:
        if brand in query_lower:
            analysis["brands"].append(brand.upper())
    
    print(f"🎯 Fallback analysis result: {analysis}")
    return analysis

def enhance_analysis_with_fallback(query: str, ai_analysis: dict) -> dict:
    """Enhance AI analysis with fallback logic"""
    fallback = fallback_analysis(query)
    
    # Use fallback values if AI didn't detect them
    if not ai_analysis.get("price_max") and fallback.get("price_max"):
        ai_analysis["price_max"] = fallback["price_max"]
    
    if not ai_analysis.get("category") and fallback.get("category"):
        ai_analysis["category"] = fallback["category"]
    
    if not ai_analysis.get("performance_level") and fallback.get("performance_level"):
        ai_analysis["performance_level"] = fallback["performance_level"]
    
    return ai_analysis

def filter_and_rank_products(query: str, analysis: dict) -> List[dict]:
    """Filter and rank products based on analysis"""
    filtered_products = []
    
    for product_data in products_data:
        # Work directly with dict to avoid encoding issues
        score = 0
        
        # Category matching
        if analysis.get('category'):
            if product_data['หมวดหมู่'].upper() == analysis['category'].upper():
                score += 100
        
        # Price filtering - STRICT enforcement
        current_price = extract_price_from_string(product_data['ราคาปัจจุบัน'])
        
        # If price_max is specified, exclude products over that price
        if analysis.get('price_max'):
            if current_price > analysis['price_max']:
                continue  # Skip this product entirely
                
        # If price_min is specified, exclude products under that price  
        if analysis.get('price_min'):
            if current_price < analysis['price_min']:
                continue  # Skip this product entirely
        
        # Give base score for products that pass price filter
        score = 10
        
        # Keyword matching in product name and description
        text_to_search = f"{product_data['ชื่อสินค้า']} {product_data['คำอธิบายสินค้า']}".lower()
        query_lower = query.lower()
        
        # Performance level matching (high priority for gaming queries)
        if analysis.get('performance_level') == 'gaming':
            gaming_keywords = ['gaming', 'geforce', 'rtx', 'gtx', 'radeon', 'rx']
            if any(keyword in text_to_search for keyword in gaming_keywords):
                score += 200  # High score for gaming performance
        
        # Brand matching (high priority)
        brands = analysis.get('brands') or []
        for brand in brands:
            if brand and brand.lower() in text_to_search:
                score += 150
        
        # Direct query match
        if query_lower in text_to_search:
            score += 100
        
        # Keyword matching
        keywords = analysis.get('keywords') or []
        for keyword in keywords:
            if keyword and keyword.lower() in text_to_search:
                score += 80
        
        # Price value scoring (closer to budget limit = higher score)
        if analysis.get('price_max'):
            price_ratio = current_price / analysis['price_max']
            if price_ratio <= 1.0:  # Within budget
                score += int((1.0 - price_ratio) * 50)  # Higher score for better value
        
        # Popularity boost (views) - reduced impact
        views_count = int(product_data['views'].replace(',', '')) if product_data['views'].replace(',', '').isdigit() else 0
        score += min(views_count / 2000, 30)  # Max 30 points from popularity
        
        # Discount boost
        if product_data['ส่วนลด'] and product_data['ส่วนลด'] != "-" and product_data['ส่วนลด'] != "ไม่มี":
            score += 25
        
        filtered_products.append((product_data, score))
    
    # Sort by score (descending) and return top 20
    filtered_products.sort(key=lambda x: x[1], reverse=True)
    return [product_data for product_data, score in filtered_products[:20]]

def generate_suggestions(partial_query: str) -> List[str]:
    """Generate search suggestions based on partial query"""
    suggestions = []
    partial_lower = partial_query.lower()
    
    # Common search patterns
    common_searches = [
        "โน้ตบุ๊คสำหรับเกม",
        "โน้ตบุ๊คทำงาน",
        "คอมพิวเตอร์ประกอบ",
        "การ์ดจอ RTX",
        "เมาส์เกมมิ่ง",
        "คีย์บอร์ดไฟ",
        "หูฟังเกม",
        "จอมอนิเตอร์ 4K",
        "SSD 1TB",
        "RAM 16GB"
    ]
    
    # Filter suggestions based on partial query
    for suggestion in common_searches:
        if partial_lower in suggestion.lower() or suggestion.lower().startswith(partial_lower):
            suggestions.append(suggestion)
    
    # Add category-based suggestions
    categories = ["NOTEBOOK", "DESKTOP", "MONITOR", "KEYBOARD", "MOUSE"]
    for category in categories:
        if partial_lower in category.lower():
            suggestions.append(f"{category} แนะนำ")
    
    return suggestions[:5]

@app.post("/api/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    try:
        # Analyze query with AI
        analysis = analyze_query_with_ai(request.query, request.llm_provider)
        
        # Filter and rank products
        products = filter_and_rank_products(request.query, analysis)
        
        # Generate suggestions
        suggestions = generate_suggestions(request.query)
        
        # Create detailed ranking explanation
        ranking_explanation = f"พบสินค้า {len(products)} รายการ"
        
        filters_applied = []
        if analysis.get('category'):
            filters_applied.append(f"หมวดหมู่: {analysis['category']}")
        
        if analysis.get('price_max'):
            filters_applied.append(f"ราคาไม่เกิน: {analysis['price_max']:,} บาท")
        elif analysis.get('price_min'):
            filters_applied.append(f"ราคาขั้นต่ำ: {analysis['price_min']:,} บาท")
            
        if analysis.get('performance_level'):
            performance_text = {
                'gaming': 'สำหรับเล่นเกม',
                'entry': 'สำหรับทำงาน', 
                'high': 'ประสิทธิภาพสูง'
            }
            filters_applied.append(f"ประเภท: {performance_text.get(analysis['performance_level'], analysis['performance_level'])}")
            
        if analysis.get('brands') and analysis['brands']:
            filters_applied.append(f"ยี่ห้อ: {', '.join(analysis['brands'])}")
            
        if filters_applied:
            ranking_explanation += f" ที่ตรงตามเงื่อนไข: {' | '.join(filters_applied)}"
        
        ranking_explanation += f" (เรียงตามความเหมาะสมและความนิยม)"
        
        return SearchResponse(
            products=products,
            suggestions=suggestions,
            ranking_explanation=ranking_explanation
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(partial_query: str):
    try:
        suggestions = generate_suggestions(partial_query)
        return SuggestionsResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "JIB Computer Shop AI Search API", "status": "running"}

# MongoDB utility functions
def refresh_products_data():
    """Refresh product data from MongoDB"""
    global products_data
    products_data = load_products()
    return len(products_data)

@app.get("/api/refresh")
async def refresh_data():
    """API endpoint to refresh products data from MongoDB"""
    try:
        count = refresh_products_data()
        return {"status": "success", "message": f"Refreshed {count} products from MongoDB"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)