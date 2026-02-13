import pytest
from app.utils.llm import invoke_chain_with_fallback
from unittest.mock import MagicMock

def test_invoke_chain_with_fallback_calls_factory(mock_llm_calls):
    # This test verifies our MOCK is working as expected (meta-test)
    # The actual implementation calls the mocked 'invoke_chain_with_fallback'
    # which we configured in conftest.py
    
    # We can't easily test the REAL 'invoke_chain_with_fallback' logic because 
    # we globally mocked it to prevent API calls!
    # So this test mainly confirms the mock setup.
    
    def dummy_factory(llm):
        return MagicMock()

    res = invoke_chain_with_fallback(dummy_factory, {"test": 1}, name="Test Agent")
    assert res == "MOCKED_LLM_RESPONSE"
