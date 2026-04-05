import asyncio
import icmplib

async def ping():
    targets = ["186.202.131.1", "5.6.7.8", "184.107.126.165", "5.7.8.9"]
    results = await icmplib.async_multiping(targets, count=5, interval=0.5, privileged=False)
    results_dict = []
    for r in results:
        rdict = {}
        for attr in dir(r):
            if attr[0] != "_":
                rdict[attr] = getattr(r, attr)
        results_dict.append(rdict)
    print(results_dict)

asyncio.run(ping())