"""LinkdAPI client wrapper for profile discovery"""

import asyncio
from typing import Optional, Dict, Tuple
from linkdapi import AsyncLinkdAPI


class LeadsAPIClient:
    """Wrapper for LinkdAPI client focused on leads discovery"""

    def __init__(self, api_key: str, max_retries: int = 3, retry_delay: int = 2, log_callback=None):
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.log_callback = log_callback

    def _log(self, message: str):
        """Log a message using callback if available"""
        if self.log_callback:
            self.log_callback(message)

    async def _make_api_call_with_retry(self, api_call, identifier: str):
        """Make an API call with retry logic"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await api_call()

                if not response:
                    last_error = "Empty response"
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return False, last_error

                if 'success' in response and not response['success']:
                    last_error = response.get('message', 'Unknown error')

                    non_retryable = ["not found", "doesn't exist", "cannot be displayed"]
                    if any(keyword in last_error.lower() for keyword in non_retryable):
                        return False, last_error

                    if attempt < self.max_retries - 1:
                        if attempt == 0:
                            self._log(f"[yellow]⚠ ({identifier}) {last_error[:60]}... retrying[/]")
                        await asyncio.sleep(1)
                        continue
                    return False, last_error

                if 'success' in response and response['success']:
                    return True, response

                last_error = "Invalid response format"
                return False, last_error

            except Exception as e:
                last_error = str(e)

                if "429" in last_error or "too many requests" in last_error.lower():
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (attempt + 1)
                        if attempt == 0:
                            self._log(f"[yellow]⏳ ({identifier}) Rate limit hit - waiting {wait_time}s[/]")
                        await asyncio.sleep(wait_time)
                        continue
                    return False, "Rate limit exceeded"

                if attempt < self.max_retries - 1:
                    if attempt == 0:
                        self._log(f"[yellow]⚠ ({identifier}) Error: {last_error[:60]}... retrying[/]")
                    await asyncio.sleep(self.retry_delay)
                    continue

        return False, last_error or "Max retries exceeded"

    async def get_full_profile(self, api: AsyncLinkdAPI, username: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Get full profile from username
        Returns: (success, full_profile_data, error_message)
        """
        success, response = await self._make_api_call_with_retry(
            lambda: api.get_full_profile(username),
            username
        )

        if not success:
            return False, None, response

        if 'data' not in response or not response['data']:
            return False, None, "No data in response"

        profile_data = response['data']
        if not profile_data.get('urn') or not profile_data.get('username'):
            return False, None, "Invalid profile data structure"

        return True, profile_data, None

    async def get_similar_profiles(self, api: AsyncLinkdAPI, urn: str) -> Tuple[bool, list, Optional[str]]:
        """
        Get similar profiles for a given URN
        Returns: (success, profiles_list, error_message)
        """
        success, response = await self._make_api_call_with_retry(
            lambda: api.get_similar_profiles(urn),
            urn[:20]
        )

        if not success:
            return False, [], response

        if 'data' not in response or not isinstance(response['data'], list):
            return False, [], "Invalid data format"

        profiles = response['data']

        valid_profiles = [
            profile for profile in profiles
            if profile.get('urn') and profile.get('id')
        ]

        return True, valid_profiles, None

    async def get_full_profiles_batch(self, api: AsyncLinkdAPI, usernames: list) -> list:
        """
        Get full profiles for a list of usernames concurrently
        Returns: list of (username, success, profile_data, error_message) tuples
        """
        async def fetch_one(username: str):
            success, profile, error = await self.get_full_profile(api, username)
            return (username, success, profile, error)

        results = await asyncio.gather(*[fetch_one(username) for username in usernames])
        return results