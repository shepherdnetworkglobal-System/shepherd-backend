import httpx
from app.core.config import settings


class StellarService:
    @staticmethod
    async def verify_transaction(tx_hash: str) -> bool:
        """
        Queries Stellar Horizon to verify if a transaction succeeded on-chain.
        """
        url = f"{settings.STELLAR_HORIZON_URL}/transactions/{tx_hash}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("successful", False)
            return False


stellar_service = StellarService()