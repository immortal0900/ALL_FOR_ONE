import asyncio
from tools.pre_promise_competition_tool_v2 import pre_promise

async def main():
    print("Testing Pre-Promise Competition Tool...")
    res = await pre_promise("서울특별시 강동구")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
