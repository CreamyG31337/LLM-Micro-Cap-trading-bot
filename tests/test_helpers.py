"""
Test helper functions for creating mock objects and common test utilities.
"""

from portfolio.fund_manager import Fund, RepositorySettings


def create_mock_fund(fund_id: str = "test", name: str = "TEST", fund_type: str = "test") -> Fund:
    """Create a mock fund for testing purposes.
    
    Args:
        fund_id: Fund ID
        name: Fund name
        fund_type: Type of fund (test, investment, rrsp, tfsa, etc.)
        
    Returns:
        Mock Fund object
    """
    return Fund(
        id=fund_id,
        name=name,
        description=f"Test {fund_type.title()} Fund",
        repository=RepositorySettings(type="csv", settings={})
    )
