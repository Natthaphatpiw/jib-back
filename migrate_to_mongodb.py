#!/usr/bin/env python3
"""
Script to migrate product data from JSON file to MongoDB
"""

import json
from pymongo import MongoClient

def migrate_json_to_mongodb():
    """Migrate product data from JSON file to MongoDB"""
    
    # MongoDB connection
    mongodb_uri = "mongodb+srv://natthaphattoichatturat:0831099362p@cluster0.rsdqqr7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        # Connect to MongoDB
        print("🔗 Connecting to MongoDB...")
        client = MongoClient(mongodb_uri)
        db = client.shopdb
        collection = db.jib_chatbot
        
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        
        # Load JSON data
        print("📂 Loading JSON file...")
        with open('jib_products_pages_1_to_5.json', 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        print(f"📊 Found {len(products_data)} products in JSON file")
        
        # Clear existing collection (optional - remove if you want to keep existing data)
        print("🗑️ Clearing existing collection...")
        collection.delete_many({})
        
        # Insert products into MongoDB
        print("⬆️ Inserting products into MongoDB...")
        if products_data:
            result = collection.insert_many(products_data)
            print(f"✅ Successfully inserted {len(result.inserted_ids)} products")
        else:
            print("⚠️ No products to insert")
        
        # Verify insertion
        count = collection.count_documents({})
        print(f"📊 Total products in MongoDB: {count}")
        
        # Show sample document
        sample = collection.find_one({})
        if sample:
            print("📄 Sample document:")
            print(json.dumps({k: v for k, v in sample.items() if k != '_id'}, ensure_ascii=False, indent=2)[:300] + "...")
        
        print("🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    finally:
        if 'client' in locals():
            client.close()
    
    return True

if __name__ == "__main__":
    migrate_json_to_mongodb()