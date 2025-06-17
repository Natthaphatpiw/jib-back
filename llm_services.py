import json
import os
import re
from typing import Dict, Any
import openai
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client with API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# LLM 1: Query Filter System
def create_mongodb_filter(user_query: str) -> dict:
    """
    LLM 1: Analyze user query and create MongoDB filter
    """
    
    # Available categories for reference
    available_categories = [
        "APPLE PRODUCTS", "กล้อง / กล้องวงจรปิด", "คอนเทนต์ ครีเอเตอร์", "คอมพิวเตอร์ฮาร์ดแวร์",
        "คอมพิวเตอร์เซ็ต", "คีย์บอร์ด / เมาส์ / เมาส์ปากกา", "จอคอมพิวเตอร์", "ชุดระบายความร้อน",
        "ทีวี", "ระบบขายหน้าร้าน", "ลำโพง / หูฟัง", "สมาร์ทโฟน และแท็บเล็ต", "สินค้าสำหรับองค์กร",
        "อุปกรณ์ขุดเหรียญคริปโต", "อุปกรณ์ตกแต่งเคส", "อุปกรณ์สำนักงาน", "อุปกรณ์เกมมิ่งเกียร์",
        "อุปกรณ์เน็ตเวิร์ค", "อุปกรณ์เสริม", "เครื่องพิมพ์ หมึก ดรัม และสแกนเนอร์", "เครื่องสำรองไฟ",
        "เครื่องใช้ไฟฟ้าภายในบ้าน", "เซิร์ฟเวอร์", "เดสก์ท็อป / ออลอินวัน / มินิพีซี",
        "เมมโมรี่การ์ด / ฮาร์ดดิสก์", "เว็บแคม / อุปกรณ์สำหรับการประชุม", "โดรน", "โน้ตบุ๊ค",
        "โปรเจคเตอร์", "โปรแกรมคอมพิวเตอร์", "ไลฟ์สไตล์ & แก็ดเจ็ต"
    ]
    
    # Common gaming keywords
    gaming_keywords = ["gaming", "เกม", "เล่นเกม", "แรง", "ประสิทธิภาพสูง", "RTX", "GTX", "GPU", "การ์ดจอ"]
    
    system_prompt = f"""คุณเป็นผู้เชี่ยวชาญในการวิเคราะห์ความต้องการของลูกค้าและสร้างตัวกรอง MongoDB

ข้อมูลสินค้ามี schema ดังนี้:
- brand: ยี่ห้อสินค้า (string)
- category: หมวดหมู่สินค้า (string) 
- name: ชื่อสินค้า (string)
- detail: รายละเอียดสินค้า (string)
- price: ราคาเดิม (integer)
- sellprice: ราคาขาย (integer)
- discount: ส่วนลดเปอร์เซ็นต์ (integer)
- views: จำนวนการดู (integer)
- warranty: การรับประกัน (string)

หมวดหมู่ที่มี:
{json.dumps(available_categories, ensure_ascii=False, indent=2)}

กฎการแปลงคำและหมวดหมู่:

**หมวดหมู่สินค้า:**
- "โน้ตบุค", "โน้คบุค", "โน้ตบุ๊ค", "notebook", "laptop" → category: "โน้ตบุ๊ค"
- "คอม", "คอมพิวเตอร์", "desktop", "pc" → category: "เดสก์ท็อป|คอมพิวเตอร์"
- "แรม", "ram", "memory" → category: "เมมโมรี่การ์ด|คอมพิวเตอร์ฮาร์ดแวร์"
- "การ์ดจอ", "vga", "graphics card", "gpu" → category: "คอมพิวเตอร์ฮาร์ดแวร์"
- "เมาส์", "mouse" → category: "คีย์บอร์ด / เมาส์"
- "คีย์บอร์ด", "keyboard" → category: "คีย์บอร์ด / เมาส์"
- "จอ", "จอมอนิเตอร์", "monitor" → category: "จอคอมพิวเตอร์"

**วัตถุประสงค์การใช้งาน:**
- "เล่นเกม", "gaming", "เกม", "แรง", "ประสิทธิภาพสูง" → ใช้ $or กับ name/detail: "gaming|เกม|แรง|MSI|ROG|Legion|TUF|RTX|GTX|ASUS|Predator|เกมมิ่ง|Core.*Ultra|RTX.*[0-9]{4}|GTX.*[0-9]{3,4}|240Hz|144Hz|รีเฟรชเรต"
- "ทำงาน", "office", "ออฟฟิศ", "excel", "โรงพยาบาล" → ใช้ $or กับ name/detail: "office|ทำงาน|business|productivity|Office.*Home|Excel|Word|PowerPoint|บางเฉียบ|เบา|แบตเตอรี่.*[0-9]+.*ชั่วโมง|พกพาสะดวก"
- "ราคาถูก", "ประหยัด", "budget" → เรียง sellprice จากน้อยไปมาก
- "คุ้มค่า", "ดีที่สุด", "แนะนำ" → ใช้ views $gte 1000 (สินค้าที่คนดูเยอะ = นิยม)

**คุณสมบัติเชิงลึกจาก detail:**
- "แรงๆ", "สปีดสูง", "เร็ว" → detail regex: "Core.*i[7-9]|Core.*Ultra|Ryzen.*[7-9]|RTX.*[4-9][0-9]{2,3}|GTX.*[1-4][0-9]{2,3}|DDR5|PCIe.*4|NVMe.*M\\\\.2|SSD.*[5-9][0-9]{2}GB|1TB"
- "เหมาะทำงาน", "ใช้งานทั่วไป" → detail regex: "Office|Word|Excel|PowerPoint|เอกสาร|ประชุม|บางเบา|พกพา|แบต.*[1-2][0-9].*ชั่วโมง"
- "เหมาะเล่นเกม" → detail regex: "เกม|gaming|RTX|GTX|240Hz|144Hz|120Hz|รีเฟรช|IPS.*panel|QHD|4K|GeForce|Radeon.*RX"
- "คุ้มค่า", "ราคาดี" → sellprice range ปานกลางของหมวดหมู่ + views $gte 500
- "พรีเมียม", "หรูหรา", "ดีไซน์สวย" → detail regex: "พรีเมียม|premium|ดีไซน์|design|บางเฉียบ|อลูมิเนียม|โลหะ|carbon|fiber"
- "ใหม่ล่าสุด", "รุ่นใหม่" → detail regex: "2024|2025|ล่าสุด|ใหม่|รุ่นใหม่|Ultra.*[0-9]|M[3-4]|13th.*Gen|14th.*Gen"
- "ทนทาน", "แข็งแรง" → detail regex: "ทนทาน|แข็งแรง|durable|military|grade|เหล็ก|อลูมิเนียม|carbon"
- "จอใหญ่", "หน้าจอใหญ่" → detail regex: "[2-3][0-9].*นิ้ว|[2-3][0-9].*inch|27.*นิ้ว|32.*นิ้ว|24.*นิ้ว"
- "จอสวย", "จอคมชัด" → detail regex: "4K|QHD|2K|Retina|IPS|OLED|HDR|sRGB|Adobe.*RGB|DCI.*P3"

**งบประมาณ:**
- "งบ X", "ราคา X", "ไม่เกิน X", "งบประมาณ X" → sellprice $lte X
- "ราคาถูก" → sellprice $lte 1000 (สำหรับอุปกรณ์เสริม)

**การเปรียบเทียบ:**
- "เท่า macbook", "เท่า mac", "แรงเท่า" → price range 25000-50000

วิเคราะห์คำถามและสร้าง MongoDB filter แบบ 2 ขั้นตอน:

**ขั้นตอนที่ 1: Basic Filter**
1. ระบุหมวดหมู่ (category regex)
2. ระบุงบประมาณ (sellprice range)
3. ระบุยี่ห้อ (brand regex)

**ขั้นตอนที่ 2: Advanced Detail Analysis**
4. วิเคราะห์ความต้องการเชิงลึกจาก user input
5. สร้าง detail regex patterns เพื่อค้นหาคุณสมบัติเฉพาะ
6. เพิ่มเงื่อนไข views สำหรับความนิยม (ถ้ามี "คุ้มค่า", "แนะนำ")
7. เพิ่มเงื่อนไข complex patterns สำหรับ specs ที่เฉพาะเจาะจง

**กฎสำคัญ:**
- ใช้ $or สำหรับ multiple conditions ใน detail
- ใช้ regex patterns สำหรับ technical specs
- ถ้าไม่พบหมวดหมู่ชัดเจน ให้ search ใน name/detail ทั้งหมด
- เมื่อ user ใช้คำเชิงลึก ("แรงๆ", "คุ้มค่า") ให้เพิ่ม technical criteria

ตัวอย่าง:

1. "โน้ตบุค เล่นเกม งบ 20000" →
{{
  "filter": {{
    "category": {{"$regex": "โน้ตบุ๊ค", "$options": "i"}},
    "sellprice": {{"$lte": 20000}},
    "$or": [
      {{"name": {{"$regex": "gaming|เกม|แรง|MSI|ROG|Legion|TUF|RTX|GTX", "$options": "i"}}}},
      {{"detail": {{"$regex": "gaming|เกม|แรง|MSI|ROG|Legion|TUF|RTX|GTX|GeForce|Radeon.*RX|144Hz|120Hz", "$options": "i"}}}}
    ]
  }}
}}

2. "โน้ตบุคแรงๆ สำหรับเล่นเกม" →
{{
  "filter": {{
    "category": {{"$regex": "โน้ตบุ๊ค", "$options": "i"}},
    "$or": [
      {{"name": {{"$regex": "gaming|เกม|แรง|MSI|ROG|Legion|TUF|RTX|GTX", "$options": "i"}}}},
      {{"detail": {{"$regex": "Core.*i[7-9]|Core.*Ultra|Ryzen.*[7-9]|RTX.*[4-9][0-9]{{2,3}}|GTX.*[1-4][0-9]{{2,3}}|DDR5|NVMe.*M\\\\.2|SSD.*[5-9][0-9]{{2}}GB|1TB", "$options": "i"}}}}
    ]
  }}
}}

3. "โน้ตบุคเหมาะทำงาน ใช้ excel งบ 25000" →
{{
  "filter": {{
    "category": {{"$regex": "โน้ตบุ๊ค", "$options": "i"}},
    "sellprice": {{"$lte": 25000}},
    "$or": [
      {{"name": {{"$regex": "office|ทำงาน|business|productivity", "$options": "i"}}}},
      {{"detail": {{"$regex": "Office|Word|Excel|PowerPoint|เอกสาร|ประชุม|บางเบา|พกพา|แบต.*[1-2][0-9].*ชั่วโมง", "$options": "i"}}}}
    ]
  }}
}}

4. "โน้ตบุคคุ้มค่า รุ่นใหม่" →
{{
  "filter": {{
    "category": {{"$regex": "โน้ตบุ๊ค", "$options": "i"}},
    "views": {{"$gte": 500}},
    "$or": [
      {{"name": {{"$regex": "2024|2025|ล่าสุด|ใหม่|รุ่นใหม่", "$options": "i"}}}},
      {{"detail": {{"$regex": "2024|2025|ล่าสุด|ใหม่|รุ่นใหม่|Ultra.*[0-9]|M[3-4]|13th.*Gen|14th.*Gen", "$options": "i"}}}}
    ]
  }}
}}

5. "จอคอมพิวเตอร์ จอใหญ่ จอสวย" →
{{
  "filter": {{
    "category": {{"$regex": "จอคอมพิวเตอร์", "$options": "i"}},
    "$or": [
      {{"name": {{"$regex": "[2-3][0-9].*นิ้ว|[2-3][0-9].*inch|4K|QHD|2K", "$options": "i"}}}},
      {{"detail": {{"$regex": "[2-3][0-9].*นิ้ว|[2-3][0-9].*inch|4K|QHD|2K|Retina|IPS|OLED|HDR|sRGB", "$options": "i"}}}}
    ]
  }}
}}

6. "เมาส์เกมมิ่ง ราคาถูก" →
{{
  "filter": {{
    "category": {{"$regex": "คีย์บอร์ด / เมาส์", "$options": "i"}},
    "sellprice": {{"$lte": 1500}},
    "$or": [
      {{"name": {{"$regex": "เมาส์|mouse|gaming|เกม", "$options": "i"}}}},
      {{"detail": {{"$regex": "gaming|เกม|DPI|RGB|optical|laser|wireless", "$options": "i"}}}}
    ]
  }}
}}

ตอบเป็น JSON object เท่านั้น:
{{
  "filter": {{ mongodb_filter_object }},
  "explanation": "คำอธิบายสั้นๆ ว่าทำไมใช้เงื่อนไขนี้"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ลูกค้าต้องการ: {user_query}"}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content.strip())
        return result
        
    except Exception as e:
        print(f"Error in create_mongodb_filter: {e}")
        return {
            "filter": {},
            "explanation": "ไม่สามารถสร้างตัวกรองได้ จะค้นหาทั้งหมด"
        }

# LLM 2: Product Analysis and Recommendation System
def analyze_and_recommend_products(user_query: str, products: list) -> dict:
    """
    LLM 2: Analyze products and create recommendations based on user needs
    """
    
    if not products:
        return {
            "recommendations": [],
            "explanation": "ไม่พบสินค้าที่ตรงกับความต้องการ",
            "total_analyzed": 0
        }
    
    # Limit products for analysis (to avoid token limits)
    products_to_analyze = products[:20]
    
    system_prompt = """คุณเป็นผู้เชี่ยวชาญด้านเทคโนโลยีและคอมพิวเตอร์ที่มีความรู้เกี่ยวกับสินค้า IT ทั้งหมด

วิเคราะห์สินค้าที่ได้รับและจัดอันดับตามความเหมาะสมกับความต้องการของลูกค้า:

หลักเกณฑ์การแนะนำ:
1. ความตรงกับความต้องการ (50%)
2. ความคุ้มค่าของราคา (25%) 
3. คุณภาพและความน่าเชื่อถือ (15%)
4. ความนิยม (10%)

ส่งคืนเป็น JSON เท่านั้น:
{
  "recommendations": [
    {
      "product_id": "id ของสินค้า",
      "rank": 1,
      "score": 95,
      "reasons": ["เหตุผลที่แนะนำ 1", "เหตุผลที่แนะนำ 2"],
      "pros": ["ข้อดี 1", "ข้อดี 2"],
      "cons": ["ข้อเสีย 1"] หรือ null ถ้าไม่มี
    }
  ],
  "explanation": "สรุปคำแนะนำโดยรวม",
  "total_analyzed": จำนวนสินค้าที่วิเคราะห์
}

จัดอันดับให้ได้สูงสุด 5 อันดับแรก เรียงจากมากไปน้อย"""

    products_summary = []
    for product in products_to_analyze:
        summary = {
            "id": product.get("id", ""),
            "name": product.get("name", ""),
            "brand": product.get("brand", ""),
            "category": product.get("category", ""),
            "price": product.get("price", 0),
            "sellprice": product.get("sellprice", 0),
            "discount": product.get("discount", 0),
            "detail": product.get("detail", "")[:200],  # Limit detail length
            "views": product.get("views", 0)
        }
        products_summary.append(summary)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ความต้องการ: {user_query}\n\nสินค้าที่จะวิเคราะห์:\n{json.dumps(products_summary, ensure_ascii=False, indent=2)}"}
            ],
            temperature=0.4,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"LLM 2 Response: {response_text}")
        
        # Try to parse JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
        
        return result
        
    except Exception as e:
        print(f"Error in analyze_and_recommend_products: {e}")
        # Return simple recommendations based on price
        simple_recommendations = []
        for i, product in enumerate(products_to_analyze[:5]):
            simple_recommendations.append({
                "product_id": product.get("id", ""),
                "rank": i + 1,
                "score": 80 - (i * 10),
                "reasons": ["ราคาเหมาะสม", "สเปคดี"],
                "pros": ["ราคาคุ้มค่า"],
                "cons": None
            })
        
        return {
            "recommendations": simple_recommendations,
            "explanation": f"พบสินค้าที่เหมาะสม {len(products_to_analyze)} รายการ จัดเรียงตามราคาและความนิยม",
            "total_analyzed": len(products_to_analyze)
        }