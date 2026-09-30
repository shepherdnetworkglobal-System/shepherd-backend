from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PayoutQuote(BaseModel):
    provider: str
    source_asset: str
    destination_currency: str
    source_amount: Decimal
    destination_amount: Decimal
    fee: Decimal
    rate: Decimal
    expires_in_seconds: int


class PayoutResult(BaseModel):
    provider: str
    provider_transaction_id: str
    destination_currency: str
    destination_amount: Decimal
    status: str
    recipient_reference: Optional[str] = None


class PayoutStatus(BaseModel):
    provider: str
    provider_transaction_id: str
    status: str
    destination_amount: Optional[Decimal] = None
    completed_at: Optional[str] = None


class BasePayoutAdapter(ABC):
    """
    All payout providers must implement this interface.
    Swap providers per country without rewriting the engine.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_countries(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def supported_methods(self) -> list[str]:
        pass

    @abstractmethod
    async def get_quote(
        self,
        source_asset: str,
        destination_currency: str,
        amount: Decimal
    ) -> PayoutQuote:
        pass

    @abstractmethod
    async def execute_payout(
        self,
        recipient_identifier: str,
        amount: Decimal,
        currency: str,
        reference: str
    ) -> PayoutResult:
        pass

    @abstractmethod
    async def check_status(
        self,
        provider_transaction_id: str
    ) -> PayoutStatus:
        pass


class ClickPesaAdapter(BasePayoutAdapter):
    """
    ClickPesa — Stellar Anchor for M-Pesa Kenya.
    Converts USDC on Stellar → KES → M-Pesa mobile money.
    Production API: https://api.clickpesa.com
    """

    @property
    def provider_name(self) -> str:
        return "clickpesa"

    @property
    def supported_countries(self) -> list[str]:
        return ["KE", "TZ", "UG"]

    @property
    def supported_methods(self) -> list[str]:
        return ["mpesa", "tigo_pesa", "mtn_mobile_money"]

    async def get_quote(
        self,
        source_asset: str,
        destination_currency: str,
        amount: Decimal
    ) -> PayoutQuote:
        # Sandbox rate: 1 USDC ≈ 129.50 KES (update with live SEP-38 quote)
        rate = Decimal("129.50")
        fee = Decimal("1.50")
        destination = (amount - fee) * rate

        return PayoutQuote(
            provider=self.provider_name,
            source_asset=source_asset,
            destination_currency=destination_currency,
            source_amount=amount,
            destination_amount=destination,
            fee=fee,
            rate=rate,
            expires_in_seconds=120
        )

    async def execute_payout(
        self,
        recipient_identifier: str,
        amount: Decimal,
        currency: str,
        reference: str
    ) -> PayoutResult:
        # Sandbox mock — replace with ClickPesa B2C API call
        # Production: POST https://api.clickpesa.com/v1/payouts
        # Body: { "phone": recipient_identifier, "amount": amount, "currency": "KES", "ref": reference }

        return PayoutResult(
            provider=self.provider_name,
            provider_transaction_id=f"CP-{reference}-SANDBOX",
            destination_currency=currency,
            destination_amount=amount,
            status="PROCESSING",
            recipient_reference=f"M-Pesa confirmation pending for {recipient_identifier}"
        )

    async def check_status(
        self,
        provider_transaction_id: str
    ) -> PayoutStatus:
        # Sandbox mock — replace with ClickPesa status polling
        return PayoutStatus(
            provider=self.provider_name,
            provider_transaction_id=provider_transaction_id,
            status="COMPLETED",
            completed_at="2026-01-15T14:30:00Z"
        )


class MoneyGramAdapter(BasePayoutAdapter):
    """
    MoneyGram Ramps — Stellar USDC Cash-Out.
    Converts USDC on Stellar → local fiat → cash pickup at MoneyGram agent.
    Production API: https://api.moneygram.com/stellar
    """

    @property
    def provider_name(self) -> str:
        return "moneygram"

    @property
    def supported_countries(self) -> list[str]:
        return ["KE", "NG", "PH", "PK", "IN", "BR", "MX", "GH"]

    @property
    def supported_methods(self) -> list[str]:
        return ["cash_pickup", "bank_deposit"]

    async def get_quote(
        self,
        source_asset: str,
        destination_currency: str,
        amount: Decimal
    ) -> PayoutQuote:
        # Sandbox rate: 1 USDC ≈ 128.00 KES (MoneyGram spread is wider)
        rate = Decimal("128.00")
        fee = Decimal("3.00")
        destination = (amount - fee) * rate

        return PayoutQuote(
            provider=self.provider_name,
            source_asset=source_asset,
            destination_currency=destination_currency,
            source_amount=amount,
            destination_amount=destination,
            fee=fee,
            rate=rate,
            expires_in_seconds=300
        )

    async def execute_payout(
        self,
        recipient_identifier: str,
        amount: Decimal,
        currency: str,
        reference: str
    ) -> PayoutResult:
        # Sandbox mock — replace with MoneyGram Stellar USDC cash-out API
        # Production: SEP-24 withdraw flow via MoneyGram anchor
        # Recipient receives MTCN reference number for cash pickup

        return PayoutResult(
            provider=self.provider_name,
            provider_transaction_id=f"MG-{reference}-SANDBOX",
            destination_currency=currency,
            destination_amount=amount,
            status="PROCESSING",
            recipient_reference=f"MTCN: 1234567890 (Cash pickup at nearest MoneyGram agent)"
        )

    async def check_status(
        self,
        provider_transaction_id: str
    ) -> PayoutStatus:
        return PayoutStatus(
            provider=self.provider_name,
            provider_transaction_id=provider_transaction_id,
            status="COMPLETED",
            completed_at="2026-01-15T15:00:00Z"
        )


class PayoutRouter:
    """
    Selects the correct adapter based on country and payout method.
    This is the single entry point the API calls.
    """

    def __init__(self):
        self.adapters: dict[str, BasePayoutAdapter] = {
            "clickpesa": ClickPesaAdapter(),
            "moneygram": MoneyGramAdapter(),
        }

    def get_adapter(
        self,
        country: str,
        method: str
    ) -> BasePayoutAdapter:
        # Priority: local mobile money first, MoneyGram as fallback
        if method in ["mpesa", "tigo_pesa", "mtn_mobile_money"]:
            return self.adapters["clickpesa"]

        if method in ["cash_pickup"]:
            return self.adapters["moneygram"]

        # Default fallback for bank deposits
        for adapter in self.adapters.values():
            if country in adapter.supported_countries and method in adapter.supported_methods:
                return adapter

        return self.adapters["moneygram"]


payout_router = PayoutRouter()