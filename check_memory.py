import asyncio
from src.main import ThreadsPoster
from src.config import Config
from src.database import Database
import json

async def check_memories():
    config = Config()
    db = Database(config)
    await db.initialize()
    
    # 獲取所有場景的記憶
    contexts = ['base', 'gaming', 'night', 'social']
    for context in contexts:
        memory = await db.get_personality_memory(context)
        print(f"\n=== {context} 場景的記憶 ===")
        print(json.dumps(memory, ensure_ascii=False, indent=2))
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(check_memories()) 