"""
usage_tracker.py - Track Gemini API usage for Muse CLI
Monitors API calls and token usage against free tier limits.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict


class UsageTracker:
    """Track and persist API usage statistics."""

    # Gemini 2.0 Flash Experimental free tier limits
    FREE_TIER_LIMITS = {
        "requests_per_minute": 15,
        "requests_per_day": 1500,
        "tokens_per_day": 1_000_000
    }

    def __init__(self):
        """Initialize the usage tracker with persistent storage."""
        self.config_dir = Path.home() / ".muse-cli"
        self.usage_file = self.config_dir / "usage.json"
        self._ensure_config_dir()
        self.data = self._load_usage()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_usage(self) -> Dict:
        """Load usage data from file."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    # Check if we need to reset daily counters
                    last_date = data.get("last_reset_date")
                    today = str(date.today())

                    if last_date != today:
                        # Reset daily counters
                        data["daily_requests"] = 0
                        data["daily_tokens"] = 0
                        data["last_reset_date"] = today

                    return data
            except (json.JSONDecodeError, IOError):
                return self._create_default_data()
        else:
            return self._create_default_data()

    def _create_default_data(self) -> Dict:
        """Create default usage data structure."""
        return {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "daily_requests": 0,
            "daily_tokens": 0,
            "last_reset_date": str(date.today()),
            "first_use_date": str(date.today())
        }

    def _save_usage(self):
        """Persist usage data to file."""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            # Silently fail if we can't save (don't interrupt user flow)
            pass

    def track_request(self, input_tokens: int = 50, output_tokens: int = 20):
        """
        Track an API request with estimated token usage.

        Args:
            input_tokens: Estimated input tokens (default: 50 for typical quote)
            output_tokens: Estimated output tokens (default: 20 for keywords)
        """
        # Reload to get latest data (in case of concurrent usage)
        self.data = self._load_usage()

        # Update counters
        self.data["total_requests"] += 1
        self.data["total_input_tokens"] += input_tokens
        self.data["total_output_tokens"] += output_tokens
        self.data["daily_requests"] += 1
        self.data["daily_tokens"] += (input_tokens + output_tokens)

        # Save updated data
        self._save_usage()

    def get_usage_stats(self) -> Dict:
        """
        Get current usage statistics.

        Returns:
            Dictionary with usage stats and percentages
        """
        self.data = self._load_usage()

        total_tokens = self.data["total_input_tokens"] + self.data["total_output_tokens"]

        # Calculate percentages of free tier limits
        daily_request_pct = (self.data["daily_requests"] / self.FREE_TIER_LIMITS["requests_per_day"]) * 100
        daily_token_pct = (self.data["daily_tokens"] / self.FREE_TIER_LIMITS["tokens_per_day"]) * 100

        return {
            "total_requests": self.data["total_requests"],
            "total_tokens": total_tokens,
            "total_input_tokens": self.data["total_input_tokens"],
            "total_output_tokens": self.data["total_output_tokens"],
            "daily_requests": self.data["daily_requests"],
            "daily_tokens": self.data["daily_tokens"],
            "daily_request_limit": self.FREE_TIER_LIMITS["requests_per_day"],
            "daily_token_limit": self.FREE_TIER_LIMITS["tokens_per_day"],
            "daily_request_percentage": daily_request_pct,
            "daily_token_percentage": daily_token_pct,
            "last_reset_date": self.data["last_reset_date"],
            "first_use_date": self.data["first_use_date"],
            "approaching_limit": daily_request_pct > 80 or daily_token_pct > 80,
            "at_limit": daily_request_pct >= 100 or daily_token_pct >= 100
        }

    def reset_stats(self):
        """Reset all usage statistics (for testing or manual reset)."""
        self.data = self._create_default_data()
        self._save_usage()

    def check_limits(self) -> tuple[bool, str]:
        """
        Check if usage is approaching or at limits.

        Returns:
            Tuple of (is_warning, message)
        """
        stats = self.get_usage_stats()

        if stats["at_limit"]:
            return (True, "⚠️  Daily API limit reached. Usage may be throttled or blocked.")
        elif stats["approaching_limit"]:
            return (True, f"⚠️  Approaching daily API limits ({stats['daily_request_percentage']:.1f}% of requests used)")

        return (False, "")


# Global tracker instance
_tracker = None

def get_tracker() -> UsageTracker:
    """Get or create the global usage tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker
