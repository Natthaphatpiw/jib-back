from pymongo import MongoClient

# 🔧 แก้ไขตามข้อมูลของคุณ
MONGO_URI = "mongodb://admin_KLwIX:KfFGVTJafRQD6_fmu6mjofO40Y@152.42.202.84:27017,152.42.202.84:27018,152.42.202.84:27019/dashboard-scrape-dev?replicaSet=rs0&authSource=admin&authMechanism=SCRAM-SHA-1"  # หรือ URI ของคุณเช่น Atlas
DATABASE_NAME = "dashboard-scrape-dev"
COLLECTION_NAME = "productjibscrapes"

# เชื่อมต่อกับ MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# ดึงค่าที่ไม่ซ้ำใน field 'category'
distinct_categories = collection.distinct("category")

# แสดงผล
print("ค่าที่ไม่ซ้ำใน category:")
for category in distinct_categories:
    print("-", category)
