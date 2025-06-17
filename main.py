import json
import os
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pymongo import MongoClient
from llm_services import create_mongodb_filter, analyze_and_recommend_products

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

class SearchResponse(BaseModel):
    products: List[Product]
    explanation: str
    total_found: int
    recommendations: List[dict]

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

@app.get("/")
def read_root():
    return {"message": "JIB Computer Shop AI Search API", "version": "2.0"}

@app.get("/health")
def health_check():
    try:
        db = get_mongodb_connection()
        if db is None:
            return {"status": "unhealthy", "database": "disconnected"}
        
        # Test database connection
        collection = db.productjibscrapes
        count = collection.count_documents({})
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_products": count,
            "categories": len(AVAILABLE_CATEGORIES)
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    New search endpoint using 2-step LLM process:
    1. LLM 1: Create MongoDB filter from query
    2. LLM 2: Analyze filtered products and provide recommendations
    """
    try:
        print(f"🔍 Processing search query: {request.query}")
        
        # Step 1: Use LLM 1 to create MongoDB filter
        print("🤖 Step 1: Creating MongoDB filter...")
        filter_result = create_mongodb_filter(request.query)
        mongodb_filter = filter_result.get("filter", {})
        filter_explanation = filter_result.get("explanation", "")
        
        print(f"📊 MongoDB filter: {mongodb_filter}")
        print(f"💭 Filter explanation: {filter_explanation}")
        
        # Step 2: Get products using the filter
        print("🔍 Step 2: Querying products from database...")
        raw_products = get_products_by_filter(mongodb_filter, limit=50)
        
        if not raw_products:
            return SearchResponse(
                products=[],
                explanation="ไม่พบสินค้าที่ตรงกับความต้องการของคุณ กรุณาลองใช้คำค้นหาอื่น",
                total_found=0,
                recommendations=[]
            )
        
        # Step 3: Use LLM 2 to analyze and recommend products
        print("🤖 Step 3: Analyzing products and creating recommendations...")
        recommendation_result = analyze_and_recommend_products(request.query, raw_products)
        
        # Step 4: Prepare response
        # Get recommended product IDs
        recommended_ids = []
        if recommendation_result.get("recommendations"):
            recommended_ids = [rec.get("product_id") for rec in recommendation_result["recommendations"]]
        
        # Sort products: recommended first, then others
        recommended_products = []
        other_products = []
        
        for product in raw_products:
            if product.get("id") in recommended_ids:
                recommended_products.append(product)
            else:
                other_products.append(product)
        
        # Combine: recommended first, then others (up to 20 total)
        sorted_products = recommended_products + other_products[:20-len(recommended_products)]
        
        # Convert to Product models
        products = []
        for product_data in sorted_products:
            try:
                product = Product(**product_data)
                products.append(product)
            except Exception as e:
                print(f"⚠️ Error converting product {product_data.get('id', 'unknown')}: {e}")
                continue
        
        return SearchResponse(
            products=products,
            explanation=recommendation_result.get("explanation", "พบสินค้าที่ตรงกับความต้องการ"),
            total_found=len(raw_products),
            recommendations=recommendation_result.get("recommendations", [])
        )
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}")

@app.post("/filter", response_model=FilterResponse)
async def create_filter(request: FilterRequest):
    """
    Create MongoDB filter from query using LLM 1
    """
    try:
        result = create_mongodb_filter(request.query)
        return FilterResponse(
            mongodb_filter=result.get("filter", {}),
            explanation=result.get("explanation", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสร้างตัวกรอง: {str(e)}")

@app.get("/categories")
def get_categories():
    """Get all available categories"""
    return {"categories": AVAILABLE_CATEGORIES}

@app.get("/products/sample")
def get_sample_products():
    """Get sample products for testing"""
    try:
        products = get_products_by_filter({}, limit=5)
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)