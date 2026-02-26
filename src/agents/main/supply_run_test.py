from agents.analysis.supply_demand_agent import supply_demand_graph
import asyncio

async def run():
    invoke = await supply_demand_graph.ainvoke({
        "start_input": {
            "target_area": "서울 송파구 석촌동"
        }
    })
    print(invoke['supply_demand_output']['pre_promise_competition'])
    return invoke


if __name__ == "__main__":
    print(asyncio.run(run()))