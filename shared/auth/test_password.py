"""Unit tests for PasswordHandler"""

import pytest
from .password import PasswordHandler


class TestPasswordHandler:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123!"
        hashed = PasswordHandler.hash_password(password)
        
        # Hash should not be empty
        assert hashed
        # Hash should not be the plain password
        assert hashed != password
        # Hash should start with bcrypt identifier
        assert hashed.startswith("$2b$")
    
    def test_hash_password_different_each_time(self):
        """Test that hashing the same password produces different hashes (salt)"""
        password = "TestPassword123!"
        hash1 = PasswordHandler.hash_password(password)
        hash2 = PasswordHandler.hash_password(password)
        
        # Hashes should be different due to different salts
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = PasswordHandler.hash_password(password)
        
        # Verification should succeed
        assert PasswordHandler.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = PasswordHandler.hash_password(password)
        
        # Verification should fail
        assert PasswordHandler.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash"""
        password = "TestPassword123!"
        invalid_hash = "not-a-valid-hash"
        
        # Should return False for invalid hash
        assert PasswordHandler.verify_password(password, invalid_hash) is False
    
    def test_is_password_strong_valid(self):
        """Test password strength validation with valid password"""
        password = "TestPassword123!"
        is_strong, error = PasswordHandler.is_password_strong(password)
        
        assert is_strong is True
        assert error is None
    
    def test_is_password_strong_too_short(self):
        """Test password strength validation with too short password"""
        password = "Test1!"
        is_strong, error = PasswordHandler.is_password_strong(password)
        
        assert is_strong is False
        assert "at least 8 characters" in error
    
    def test_is_password_strong_no_uppercase(self):
        """Test password strength validation without uppercase letter"""
        password = "testpassword123!"
        is_strong, error = PasswordHandler.is_password_strong(password)
        
        assert is_strong is False
        assert "uppercase letter" in error
    
    def test_is_password_strong_no_lowercase(self):
        """Test password strength validation without lowercase letter"""
        password = "TESTPASSWORD123!"
        is_strong, error = PasswordHandler.is_password_strong(password)
        
        assert is_strong is False
        assert "lowercase letter" in error
    
    def test_is_password_strong_no_digit(self):
        """Test password strength validation without digit"""
        password = "TestPassword!"
        is_strong, error = PasswordHandler.is_password_strong(password)
        
        assert is_strong is False
        assert "digit" in error
    
    def test_is_password_strong_no_special_char(self):
        """Test password strength validation without special character"""
        password = "TestPassword123"
        is_strong, error = PasswordHandler.is_password_strong(password)
        
        assert is_strong is False
        assert "special character" in error
    
    def test_is_password_strong_all_requirements(self):
        """Test various valid passwords meeting all requirements"""
        valid_passwords = [
            "Password1!",
            "MyP@ssw0rd",
            "Str0ng#Pass",
            "C0mpl3x$P@ss",
            "V3ry-S3cur3!"
        ]
        
        for password in valid_passwords:
            is_strong, error = PasswordHandler.is_password_strong(password)
            assert is_strong is True, f"Password '{password}' should be valid"
            assert error is None
    
    def test_password_roundtrip(self):
        """Test complete password hash and verify workflow"""
        passwords = [
            "TestPassword123!",
            "MyP@ssw0rd2024",
            "Str0ng#SecurePass",
        ]
        
        for password in passwords:
            # Hash the password
            hashed = PasswordHandler.hash_password(password)
            
            # Verify the correct password
            assert PasswordHandler.verify_password(password, hashed) is True
            
            # Verify wrong passwords fail
            assert PasswordHandler.verify_password(password + "wrong", hashed) is False
            assert PasswordHandler.verify_password("", hashed) is False
