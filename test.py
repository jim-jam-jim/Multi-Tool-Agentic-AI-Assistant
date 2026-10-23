import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "arith": {
        "transport": "stdio",
        "command": "python",
        "args": [r"C:\Users\Aryan Raj\Desktop\mcp-math-server\main.py"],
    },
    "expense": {
        "transport": "streamable_http",
        "url": "https://splendid-gold-dingo.fastmcp.app/mcp",
    },
})

async def main():
    for server in ("arith", "expense"):
        print(f"\n===== {server} =====")
        try:
            tools = await client.get_tools(server_name=server)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue
        for t in tools:
            print(f"\n  name   : {t.name}")
            print(f"  desc   : {(t.description or '').strip()[:120]}")
            print(f"  schema : {t.args}")

asyncio.run(main())