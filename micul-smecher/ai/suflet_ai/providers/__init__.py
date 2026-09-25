"""How SOUL understands a request: offline rules, Claude, or ChatGPT.

Every provider turns text into the same SOUL actions (see ../actions.py) and
returns the same AskResult, so the device screens and tests are shared.
"""
from .base import AskContext, AskResult, Provider, ProviderError

__all__ = ["AskContext", "AskResult", "Provider", "ProviderError"]
