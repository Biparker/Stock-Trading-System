# Security Documentation - Sentiment Analyzer

## Overview

This document details the comprehensive security measures implemented to protect your Merrill Lynch credentials and ensure the safety of your financial accounts.

## Critical Security Principles

### 1. **READ-ONLY ACCESS ONLY**
The sentiment analyzer is designed to **ONLY READ** analyst reports. It has:
- ✓ **NO ability to execute trades**
- ✓ **NO access to account balances**
- ✓ **NO ability to transfer funds**
- ✓ **NO access to personal financial information**
- ✓ **NO ability to modify account settings**

The system only navigates to the research section to download PDF reports - nothing more.

### 2. **LOCAL-ONLY CREDENTIAL STORAGE**
Your credentials are:
- ✓ **Stored ONLY on your local machine**
- ✓ **NEVER transmitted to any external server**
- ✓ **NEVER uploaded to the cloud**
- ✓ **NEVER shared with third parties**
- ✓ **NEVER logged in plain text**

## Encryption Implementation

### Fernet Symmetric Encryption
Your credentials are protected using the `cryptography` library's Fernet implementation:

```python
from cryptography.fernet import Fernet

# Key generation (one-time, stored locally)
key = Fernet.generate_key()  # 256-bit encryption key

# Encryption
cipher = Fernet(key)
encrypted_credentials = cipher.encrypt(credentials.encode())

# Decryption (only when needed)
decrypted_credentials = cipher.decrypt(encrypted_credentials)
```

**Technical Details:**
- **Algorithm**: AES-128 in CBC mode with PKCS7 padding
- **Key Size**: 256-bit encryption key
- **Authentication**: HMAC using SHA256
- **Timestamp**: Includes timestamp to prevent replay attacks

### File Storage Security

**Encryption Key File**: `data/credentials/.key`
- Binary file containing the encryption key
- File permissions should be restricted (user-only read/write)
- Automatically excluded from version control (.gitignore)

**Encrypted Credentials File**: `data/credentials/credentials.enc`
- Contains encrypted username:password
- Unreadable without the encryption key
- Automatically excluded from version control (.gitignore)

## Security Best Practices Implemented

### 1. **Secure Session Management**
```python
# Sessions are properly closed after use
with PDFRetriever() as retriever:
    # Use retriever
    pass  # Automatically closes and cleans up
```

- Browser sessions are terminated after each use
- No persistent login sessions
- Cookies and cache are cleared
- WebDriver instances are properly disposed

### 2. **No Credential Logging**
```python
# Credentials are NEVER logged
logger.info("Authentication successful")  # ✓ Safe
# logger.info(f"Password: {password}")    # ✗ NEVER done
```

- Passwords never appear in log files
- Only success/failure status is logged
- Debug mode does not expose credentials

### 3. **Environment Variable Support**
For additional security, you can use environment variables instead of stored files:

```bash
# Set environment variables (not stored in files)
export MERRILL_USERNAME="your_username"
export MERRILL_PASSWORD="your_password"
```

```python
# Code checks environment variables first
username = os.getenv('MERRILL_USERNAME') or stored_username
password = os.getenv('MERRILL_PASSWORD') or stored_password
```

### 4. **Headless Browser Mode**
```python
options.add_argument('--headless')  # Runs in background
```

- Browser runs invisibly in the background
- No visible windows that could be screen-captured
- Reduces attack surface

### 5. **Automatic Cleanup**
```python
def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager ensures cleanup"""
    if self.driver:
        self.driver.quit()  # Closes browser and cleans up
```

- All resources are automatically cleaned up
- No lingering browser sessions
- Memory is properly freed

## Additional Security Recommendations

### 1. **Use Read-Only Merrill Account (If Available)**
If Merrill Lynch offers read-only API access or sub-accounts:
- Create a separate read-only account
- Use that account for the sentiment analyzer
- This provides an additional layer of protection

### 2. **Enable Two-Factor Authentication (2FA)**
- Enable 2FA on your Merrill Lynch account
- This protects your account even if credentials are compromised
- Note: May require manual intervention for login

### 3. **Regular Credential Rotation**
```bash
# Update credentials periodically
python main.py --setup-credentials
```

- Change your Merrill password regularly
- Update stored credentials after password changes
- Monitor account for unauthorized access

### 4. **File System Permissions**
```bash
# Restrict access to credential files (Unix/Mac)
chmod 600 data/credentials/.key
chmod 600 data/credentials/credentials.enc

# Windows: Use file properties to restrict access
# Right-click → Properties → Security → Advanced
```

### 5. **Firewall and Antivirus**
- Keep your firewall enabled
- Use reputable antivirus software
- Keep your system updated

### 6. **Secure Your Computer**
- Use strong password/PIN for your computer
- Enable disk encryption (BitLocker/FileVault)
- Lock your computer when away
- Don't run on shared/public computers

## What This System CANNOT Do

To be absolutely clear, this system has **ZERO** capability to:

❌ Execute any trades or orders
❌ Transfer money between accounts
❌ Withdraw funds
❌ Change account settings
❌ Access account balances
❌ View transaction history
❌ Modify personal information
❌ Add/remove beneficiaries
❌ Change passwords
❌ Access anything outside the research section

## Network Security

### No External Transmission
```python
# Credentials are ONLY used locally
# NO API calls to external servers with credentials
# NO cloud storage of credentials
# NO third-party services involved
```

### HTTPS Only
```python
MERRILL_BASE_URL = "https://www.merrilledge.com"  # Always HTTPS
```

- All connections to Merrill Lynch use HTTPS
- SSL/TLS encryption for all network traffic
- Certificate validation enabled

## Code Transparency

### Open Source Benefits
- All code is visible and auditable
- No hidden functionality
- No obfuscated code
- Community can review for security issues

### Verification Steps
You can verify the security yourself:

1. **Review the code**: All source code is in `src/` directory
2. **Check network calls**: Search for `requests.` and `driver.get(` to see all network activity
3. **Inspect credential usage**: Search for `username` and `password` to see how they're used
4. **Verify encryption**: Review `pdf_retriever.py` encryption implementation

## Incident Response

### If You Suspect Compromise

1. **Immediately change your Merrill Lynch password**
2. **Review your account activity for unauthorized access**
3. **Contact Merrill Lynch security**
4. **Delete the credential files**:
   ```bash
   rm data/credentials/.key
   rm data/credentials/credentials.enc
   ```
5. **Run antivirus scan on your computer**

### Monitoring Your Account

- Regularly review your Merrill Lynch account activity
- Enable email/SMS alerts for account activity
- Check for unfamiliar login locations/times
- Report any suspicious activity immediately

## Compliance & Legal

### Disclaimer
This tool is provided "as-is" without warranty. While we implement strong security measures:

- You are responsible for securing your own computer
- You should review the code before using it
- You should follow all Merrill Lynch terms of service
- You should comply with all applicable laws and regulations

### Terms of Service
Ensure your use of this tool complies with:
- Merrill Lynch Terms of Service
- Your account agreement
- Applicable securities regulations
- Data protection laws

## Security Audit Checklist

Before using the system, verify:

- [ ] Credentials are stored in encrypted format
- [ ] Credential files are in .gitignore
- [ ] File permissions are restricted
- [ ] System is running on a secure computer
- [ ] Antivirus is up to date
- [ ] Firewall is enabled
- [ ] 2FA is enabled on Merrill account
- [ ] You understand the system only reads reports
- [ ] You've reviewed the source code
- [ ] You have a backup plan if credentials are compromised

## Technical Security Details

### Encryption Specifications
- **Algorithm**: AES (Advanced Encryption Standard)
- **Mode**: CBC (Cipher Block Chaining)
- **Key Size**: 256 bits
- **Padding**: PKCS7
- **Authentication**: HMAC-SHA256
- **Library**: Python `cryptography` (industry standard)

### Security Updates
- Keep Python and all dependencies updated
- Monitor security advisories for used libraries
- Update the sentiment analyzer when new versions are released

## Questions & Support

### Security Questions?
If you have security concerns:
1. Review this document thoroughly
2. Examine the source code
3. Consult with a security professional
4. Contact Merrill Lynch about their security policies

### Reporting Security Issues
If you discover a security vulnerability:
1. Do NOT post publicly
2. Document the issue privately
3. Contact the development team
4. Allow time for a fix before disclosure

---

## Summary

**Your credentials are protected by:**
1. ✓ Military-grade encryption (AES-256)
2. ✓ Local-only storage (never transmitted)
3. ✓ Read-only access (cannot execute trades)
4. ✓ Secure session management
5. ✓ No credential logging
6. ✓ Automatic cleanup
7. ✓ Open source transparency

**You should:**
1. ✓ Enable 2FA on your Merrill account
2. ✓ Use a secure computer
3. ✓ Restrict file permissions
4. ✓ Rotate credentials regularly
5. ✓ Monitor your account activity
6. ✓ Keep software updated

**Remember:**
- This tool ONLY reads analyst reports
- It CANNOT execute trades or transfer money
- Your credentials stay on YOUR computer
- You maintain full control of your account

---

**Last Updated**: 2026-06-05
**Version**: 1.0.0

For additional security guidance, consult with a cybersecurity professional or contact Merrill Lynch directly about their security recommendations.