import pytest
from app.db.vault import store_pii, retrieve_pii, deanonymize_text, _get_conn
from app.utils.pii import get_pii_scrubber

def test_vault_store_and_retrieve():
    """Test standard storage and retrieval of PII."""
    original_email = "test.user@example.com"
    entity_type = "EMAIL_ADDRESS"
    
    # Store should return a token
    token = store_pii(entity_type, original_email)
    
    # Token format should be [PII_ENTITY_xxxxxxxx]
    assert token.startswith("[PII_EMAIL_ADDRESS_")
    assert token.endswith("]")
    assert len(token) > len("[PII_EMAIL_ADDRESS_]")
    
    # Retrieve should return the original text
    retrieved = retrieve_pii(token)
    assert retrieved == original_email

def test_vault_duplicate_storage():
    """Test that storing the same PII twice returns the same token."""
    original_email = "duplicate@example.com"
    entity_type = "EMAIL_ADDRESS"
    
    token1 = store_pii(entity_type, original_email)
    token2 = store_pii(entity_type, original_email)
    
    assert token1 == token2

def test_vault_unknown_token():
    """Test that retrieving an unknown token returns the token itself."""
    fake_token = "[PII_PERSON_12345678]"
    retrieved = retrieve_pii(fake_token)
    
    assert retrieved == fake_token

def test_deanonymize_text_single():
    """Test deanonymizing a text with a single token."""
    original_phone = "555-123-4567"
    token = store_pii("PHONE_NUMBER", original_phone)
    
    anonymized_text = f"My phone number is {token}."
    expected_text = f"My phone number is {original_phone}."
    
    result = deanonymize_text(anonymized_text)
    assert result == expected_text

def test_deanonymize_text_multiple():
    """Test deanonymizing a text with multiple tokens of different types."""
    email = "multi@example.com"
    phone = "555-987-6543"
    
    email_token = store_pii("EMAIL_ADDRESS", email)
    phone_token = store_pii("PHONE_NUMBER", phone)
    
    anonymized_text = f"Contact {email_token} or {phone_token} for support."
    expected_text = f"Contact {email} or {phone} for support."
    
    result = deanonymize_text(anonymized_text)
    assert result == expected_text

def test_end_to_end_pii_scrubber():
    """Test the full flow: Scrubbing -> DB -> Deanonymizing."""
    scrubber = get_pii_scrubber()
    original_text = "Hello, my name is John Doe and my email is john.doe@example.com. Call me at 123-456-7890."
    
    # 1. Scrub (Tokenize)
    scrubbed = scrubber.scrub_text(original_text)
    
    # Verify it was tokenized (should contain tokens, not the raw PII)
    assert "john.doe@example.com" not in scrubbed
    assert "123-456-7890" not in scrubbed
    # It should have tokens
    assert "[PII_EMAIL_ADDRESS_" in scrubbed
    assert "[PII_PHONE_NUMBER_" in scrubbed
    assert "[PII_PERSON_" in scrubbed
    
    # 2. Deanonymize (Restore)
    restored = deanonymize_text(scrubbed)
    
    # Fast verify
    assert restored == original_text
