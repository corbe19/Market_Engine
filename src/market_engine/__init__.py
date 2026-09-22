"""Real-time market microstructure intelligence platform.

Subpackage layout mirrors the pipeline stages in ``plan.md`` section 5. Data
flows strictly in one direction:

    ingestion -> orderbook -> features -> labels -> models -> execution

``replay`` feeds ``orderbook`` from a recorded event log instead of a live
socket, and must produce output identical to the live path (``plan.md``
invariant 2). ``monitoring`` and ``api`` observe the pipeline; nothing in the
pipeline may import from them.
"""

__version__ = "0.0.1"

__all__ = ["__version__"]
