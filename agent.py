from enum import Enum

from uagents import Agent, Context, Model
from uagents.experimental.quota import QuotaProtocol, RateLimit
from uagents_core.models import ErrorMessage

from price_agent import PriceRequest, PriceResponse, get_price_data
from chat import chat_proto, struct_output_client_proto

# One process, mailbox=True for local testing
agent = Agent(name="stock_price_agent", port=8001, mailbox=True)
    #endpoint=["http://localhost:8001/"],
            

# ── Quota-limited public price protocol
price_proto = QuotaProtocol(
    storage_reference=agent.storage,
    name="Price-Protocol",
    version="0.1.0",
    default_rate_limit=RateLimit(window_size_minutes=60, max_requests=30),
)

@price_proto.on_message(PriceRequest, replies={PriceResponse, ErrorMessage})
async def _(ctx: Context, sender: str, msg: PriceRequest):
    ctx.logger.info(f"Price request for {msg.ticker} from {sender}")
    try:
        result = await get_price_data(msg.ticker, msg.start, msg.limit or 5_000)
        await ctx.send(sender, PriceResponse(results=result))
    except Exception as exc:
        await ctx.send(sender, ErrorMessage(error=str(exc)))

agent.include(price_proto, publish_manifest=True)

# ── Simple health-check protocol ────────────────────────────────────────────
class HealthCheck(Model):
    pass

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"

class AgentHealth(Model):
    agent_name: str
    status: HealthStatus

health_proto = QuotaProtocol(
    storage_reference=agent.storage, name="HealthProtocol", version="0.1.0"
)

@health_proto.on_message(HealthCheck, replies={AgentHealth})
async def _(ctx: Context, sender: str, _msg: HealthCheck):
    status = HealthStatus.UNHEALTHY
    try:
        import asyncio
        asyncio.run(get_price_data("SPY", limit=1))
        status = HealthStatus.HEALTHY
    except Exception as exc:
        ctx.logger.error(exc)
    finally:
        await ctx.send(sender, AgentHealth(agent_name=agent.address, status=status))

agent.include(health_proto, publish_manifest=True)

# ── Chat & structured-output client protocols ───────────────────────────────
agent.include(chat_proto, publish_manifest=True)
agent.include(struct_output_client_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
