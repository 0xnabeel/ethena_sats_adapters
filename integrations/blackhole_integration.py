from typing import Dict, List, Optional, Set
import requests
from eth_typing import ChecksumAddress
from web3 import Web3

from constants.chains import Chain
from constants.summary_columns import SummaryColumn
from integrations.cached_balances_integration import CachedBalancesIntegration
from integrations.integration_ids import IntegrationID


class BlackholeIntegration(CachedBalancesIntegration):
    """Integration for tracking Blackhole LP positions (sUSD)"""

    def __init__(
        self,
        integration_id: IntegrationID,
        start_block: int,
        chain: Chain = Chain.AVALANCHE,
        summary_cols: Optional[List[SummaryColumn]] = None,
        reward_multiplier: int = 1,
        balance_multiplier: int = 1,
        excluded_addresses: Optional[Set[ChecksumAddress]] = None,
        end_block: Optional[int] = None,
        ethereal_multiplier: int = 0,
        ethereal_multiplier_func: Optional[callable] = None,
        ticker: str = "sUSD",  # 👈 Blackhole requires ticker
    ):
        super().__init__(
            integration_id,
            start_block,
            chain,
            summary_cols,
            reward_multiplier,
            balance_multiplier,
            excluded_addresses,
            end_block,
            ethereal_multiplier,
            ethereal_multiplier_func,
        )
        self.api_url = "https://api.blackhole.xyz/v1/partner-tasks/ethena/user-balances"
        self.ticker = ticker

    def get_block_balances(
        self, cached_data: Dict[int, Dict[ChecksumAddress, float]], blocks: List[int]
    ) -> Dict[int, Dict[ChecksumAddress, float]]:
        """Fetch balances for sUSD on Blackhole by block number, handling pagination."""
        result = {}

        for block in blocks:
            if block in cached_data:
                result[block] = cached_data[block]
                continue

            block_data = {}
            page_number = 1

            try:
                while True:
                    response = requests.get(
                        self.api_url,
                        params={
                            "ticker": self.ticker,
                            "blockNumber": block,
                            "pageNumber": page_number,
                        },
                        timeout=10,
                    )
                    data = response.json()

                    if data.get("code") != 200 or data["data"].get("status") != 0:
                        print(f"Unexpected API response for block {block}, page {page_number}: {data}")
                        break

                    balances = data["data"].get("balances", {})
                    if not balances:
                        # No more pages
                        break

                    for addr, bal in balances.items():
                        checksum_addr = Web3.to_checksum_address(addr)
                        value = float(bal)
                        if value > 0:
                            # Accumulate values if the same user appears on multiple pages
                            block_data[checksum_addr] = block_data.get(checksum_addr, 0.0) + value

                    page_number += 1

            except Exception as e:
                print(f"Error fetching data for block {block}, page {page_number}: {str(e)}")

            result[block] = block_data

        return result


if __name__ == "__main__":
    # Simple test
    integration = BlackholeIntegration(
        integration_id=IntegrationID.BLACKHOLE_SUSD_POOL,
        start_block=15817416,
        chain=Chain.AVALANCHE,
        summary_cols=[SummaryColumn.BLACKHOLE_POOL_PTS],
        reward_multiplier=1,
    )

    result = integration.get_block_balances(cached_data={}, blocks=[15817416])
    print("Block balances:", result)
