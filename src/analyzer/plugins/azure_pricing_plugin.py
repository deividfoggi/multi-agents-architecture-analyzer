"""
Azure Pricing API Plugin for Azure AI agents.
Provides access to Azure Retail Prices API for cost calculation.
"""
from typing import Annotated, Optional, List, Dict, Any
import aiohttp
import logging
from urllib.parse import quote
import asyncio
import json

logger = logging.getLogger(__name__)


class AzurePricingPlugin:
    """
    Plugin that provides Azure Retail Prices API access to agents.
    
    API Documentation: https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices
    API Endpoint: https://prices.azure.com/api/retail/prices
    
    IMPORTANT: 
    - API version 2023-01-01-preview is recommended (supports savings plans)
    - Filter values are case-sensitive (e.g., 'Virtual Machines' not 'virtual machines')
    - Maximum 1000 records per response, use NextPageLink for pagination
    """
    
    BASE_URL = "https://prices.azure.com/api/retail/prices"
    API_VERSION = "2023-01-01-preview"  # Supports savings plans and latest features
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_owner = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._session_owner = True
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session if we own it"""
        if self._session_owner and self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()
    
    async def query_azure_pricing(
        self,
        service_name: Annotated[str, "Azure service name (e.g., 'Azure App Service', 'Virtual Machines', 'Azure SQL Database')"],
        region: Annotated[str, "Azure region name (e.g., 'eastus', 'westeurope', 'brazilsouth')"],
        meter_name: Annotated[Optional[str], "Specific meter/SKU name to filter (e.g., 'P1 v3', 'D4s v3')"] = None,
        product_name: Annotated[Optional[str], "Specific product name to filter"] = None,
        currency_code: Annotated[str, "Currency code for pricing (default: USD)"] = "USD"
    ) -> str:
        """
        Query Azure Retail Prices API with filters.
        
        Returns JSON string with pricing information.
        
        Example usage:
        - query_azure_pricing("Azure App Service", "eastus", "P1 v3")
        - query_azure_pricing("Virtual Machines", "westeurope", "D4s v3")
        - query_azure_pricing("Azure SQL Database", "brazilsouth", "Business Critical - 8 vCore")
        """
        try:
            # Build OData filter (NOTE: filter values are case-sensitive)
            filters = [
                f"serviceName eq '{service_name}'",
                f"armRegionName eq '{region}'"
            ]
            
            if meter_name:
                filters.append(f"meterName eq '{meter_name}'")
            
            if product_name:
                filters.append(f"productName eq '{product_name}'")
            
            filter_string = " and ".join(filters)
            encoded_filter = quote(filter_string)
            
            # Currency code should be a query parameter, not in the filter
            url = f"{self.BASE_URL}?api-version={self.API_VERSION}&currencyCode={currency_code}&$filter={encoded_filter}"
            
            logger.info(f"Querying Azure Pricing API: {service_name} in {region} (currency: {currency_code})")
            
            session = await self._get_session()
            
            # Retry logic
            for attempt in range(self.MAX_RETRIES):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get("Items", [])
                            logger.info(f"Azure Pricing API returned {len(items)} pricing items")
                            
                            # Return formatted response as JSON string
                            result = {
                                "status": "success",
                                "query": {
                                    "service": service_name,
                                    "region": region,
                                    "meter_name": meter_name,
                                    "product_name": product_name,
                                    "currency": currency_code
                                },
                                "results_count": len(items),
                                "items": items[:10],  # Limit to first 10 results
                                "next_page_link": data.get("NextPageLink")
                            }
                            return json.dumps(result, indent=2)
                        else:
                            error_text = await response.text()
                            logger.warning(f"Azure Pricing API returned status {response.status}: {error_text}")
                            
                            if attempt < self.MAX_RETRIES - 1:
                                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                                continue
                            
                            result = {
                                "status": "error",
                                "error_code": response.status,
                                "error_message": f"API request failed with status {response.status}",
                                "details": error_text[:500]
                            }
                            return json.dumps(result, indent=2)
                
                except asyncio.TimeoutError:
                    logger.warning(f"Azure Pricing API timeout (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    
                    result = {
                        "status": "error",
                        "error_code": "timeout",
                        "error_message": f"API request timed out after {self.DEFAULT_TIMEOUT}s"
                    }
                    return json.dumps(result, indent=2)
                
                except aiohttp.ClientError as e:
                    logger.warning(f"Azure Pricing API client error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    
                    result = {
                        "status": "error",
                        "error_code": "client_error",
                        "error_message": str(e)
                    }
                    return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"Unexpected error querying Azure Pricing API: {e}", exc_info=True)
            result = {
                "status": "error",
                "error_code": "unexpected",
                "error_message": str(e)
            }
            return json.dumps(result, indent=2)
    
    async def search_azure_pricing(
        self,
        odata_filter: Annotated[str, "OData filter string (e.g., \"serviceName eq 'Azure App Service' and armRegionName eq 'eastus'\")"],
        currency_code: Annotated[str, "Currency code for pricing (default: USD)"] = "USD"
    ) -> str:
        """
        Search Azure Retail Prices API with a custom OData filter.
        
        This function allows for more complex queries using OData syntax.
        
        Example filters:
        - "serviceName eq 'Azure App Service' and armRegionName eq 'eastus' and meterName eq 'P1 v3'"
        - "serviceName eq 'Virtual Machines' and armRegionName eq 'westeurope' and skuName eq 'D4s v3'"
        - "productName eq 'Azure SQL Database' and armRegionName eq 'brazilsouth'"
        """
        try:
            # Remove currencyCode from filter if present (should be query param)
            if "currencyCode" in odata_filter:
                logger.warning("currencyCode should not be in filter, using as query parameter instead")
                odata_filter = odata_filter.replace(f" and currencyCode eq '{currency_code}'", "")
                odata_filter = odata_filter.replace(f"currencyCode eq '{currency_code}' and ", "")
            
            encoded_filter = quote(odata_filter)
            # Currency code as query parameter, not in filter
            url = f"{self.BASE_URL}?api-version={self.API_VERSION}&currencyCode={currency_code}&$filter={encoded_filter}"
            
            logger.info(f"Searching Azure Pricing API with filter: {odata_filter[:100]}... (currency: {currency_code})")
            
            session = await self._get_session()
            
            # Retry logic
            for attempt in range(self.MAX_RETRIES):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get("Items", [])
                            logger.info(f"Azure Pricing API search returned {len(items)} pricing items")
                            
                            result = {
                                "status": "success",
                                "filter": odata_filter,
                                "results_count": len(items),
                                "items": items[:10],  # Limit to first 10 results
                                "next_page_link": data.get("NextPageLink")
                            }
                            return json.dumps(result, indent=2)
                        else:
                            error_text = await response.text()
                            logger.warning(f"Azure Pricing API search returned status {response.status}: {error_text}")
                            
                            if attempt < self.MAX_RETRIES - 1:
                                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                                continue
                            
                            result = {
                                "status": "error",
                                "error_code": response.status,
                                "error_message": f"API request failed with status {response.status}",
                                "details": error_text[:500]
                            }
                            return json.dumps(result, indent=2)
                
                except asyncio.TimeoutError:
                    logger.warning(f"Azure Pricing API search timeout (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    
                    result = {
                        "status": "error",
                        "error_code": "timeout",
                        "error_message": f"API request timed out after {self.DEFAULT_TIMEOUT}s"
                    }
                    return json.dumps(result, indent=2)
                
                except aiohttp.ClientError as e:
                    logger.warning(f"Azure Pricing API search client error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    
                    result = {
                        "status": "error",
                        "error_code": "client_error",
                        "error_message": str(e)
                    }
                    return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"Unexpected error searching Azure Pricing API: {e}", exc_info=True)
            result = {
                "status": "error",
                "error_code": "unexpected",
                "error_message": str(e)
            }
            return json.dumps(result, indent=2)
    
    async def get_service_pricing_summary(
        self,
        service_name: Annotated[str, "Azure service name (e.g., 'Azure App Service', 'Virtual Machines')"],
        region: Annotated[str, "Azure region name (e.g., 'eastus', 'westeurope')"],
        currency_code: Annotated[str, "Currency code for pricing (default: USD)"] = "USD"
    ) -> str:
        """
        Get a pricing summary for an Azure service in a region.
        
        Returns aggregated information about available SKUs and their pricing.
        """
        try:
            result_json = await self.query_azure_pricing(service_name, region, currency_code=currency_code)
            result = json.loads(result_json)
            
            if isinstance(result, dict) and result.get("status") == "success":
                items = result.get("items", [])
                
                # Aggregate pricing info
                skus = {}
                for item in items:
                    sku_name = item.get("skuName", "Unknown")
                    meter_name = item.get("meterName", "Unknown")
                    retail_price = item.get("retailPrice", 0)
                    unit = item.get("unitOfMeasure", "1 Hour")
                    
                    key = f"{sku_name} - {meter_name}"
                    if key not in skus or retail_price < skus[key]["price"]:
                        skus[key] = {
                            "sku": sku_name,
                            "meter": meter_name,
                            "price": retail_price,
                            "unit": unit,
                            "product_name": item.get("productName", ""),
                            "tier": item.get("serviceTier", "")
                        }
                
                summary = {
                    "status": "success",
                    "service": service_name,
                    "region": region,
                    "currency": currency_code,
                    "sku_count": len(skus),
                    "skus": list(skus.values())[:20]  # Limit to 20 SKUs
                }
                return json.dumps(summary, indent=2)
            else:
                return result_json
        
        except Exception as e:
            logger.error(f"Error getting service pricing summary: {e}", exc_info=True)
            error_result = {
                "status": "error",
                "error_code": "unexpected",
                "error_message": str(e)
            }
            return json.dumps(error_result, indent=2)
