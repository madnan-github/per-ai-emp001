# Authentication Protocols and Standards

## Overview
This document provides a comprehensive overview of authentication protocols and standards that the Authentication Manager skill supports and implements. Understanding these protocols is essential for implementing secure and interoperable authentication systems.

## OAuth 2.0

### Introduction
OAuth 2.0 is an industry-standard protocol for authorization that allows third-party applications to obtain limited access to user accounts on an HTTP service. It separates the role of the client from the resource owner, enabling secure delegated access.

### Grant Types
#### Authorization Code Grant
Used for applications that can securely store client secrets:
```
1. Client redirects user to authorization server
2. User authenticates and grants permissions
3. Authorization server redirects back with authorization code
4. Client exchanges code for access token
5. Client accesses resource server with token
```

#### Implicit Grant
Suitable for public clients like JavaScript applications:
```
1. Client redirects user to authorization server
2. User authenticates and grants permissions
3. Authorization server returns access token directly
4. Client accesses resource server with token
```

#### Resource Owner Password Credentials
For trusted first-party applications only:
```
1. User provides credentials to client
2. Client sends credentials to authorization server
3. Authorization server returns access token
4. Client accesses resource server with token
```

#### Client Credentials
For machine-to-machine communication:
```
1. Client authenticates with client credentials
2. Authorization server returns access token
3. Client accesses resource server with token
```

### OAuth 2.0 Security Considerations
- Always use PKCE (Proof Key for Code Exchange) for public clients
- Validate the redirect_uri parameter to prevent open redirect attacks
- Implement proper scope management
- Use short-lived access tokens with refresh tokens
- Implement proper token revocation mechanisms

## OpenID Connect (OIDC)

### Introduction
OpenID Connect is a simple identity layer built on top of OAuth 2.0. It enables clients to verify the identity of the end-user based on the authentication performed by an authorization server and to obtain basic profile information about the end-user.

### Core Concepts
- **ID Token**: A JWT containing claims about the authenticated user
- **UserInfo Endpoint**: Additional user information beyond the ID token
- **Discovery Endpoint**: Metadata about the OIDC provider
- **Scopes**: openid, profile, email, address, phone

### ID Token Claims
```json
{
  "iss": "https://provider.example.com",
  "sub": "subject_identifier",
  "aud": "client_id",
  "exp": 1360000000,
  "iat": 1360000000,
  "auth_time": 1360000000,
  "nonce": "random_nonce_value",
  "at_hash": "access_token_hash",
  "acr": "authentication_context_class",
  "amr": "authentication_methods_references",
  "azp": "authorized_party"
}
```

## JWT (JSON Web Tokens)

### Structure
JWTs consist of three parts separated by dots:
- **Header**: Contains token type and signing algorithm
- **Payload**: Contains claims about entities and additional data
- **Signature**: Ensures token integrity

### Header Example
```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

### Payload Claims
- **Registered Claims**: Standard claims like iss, exp, sub
- **Public Claims**: Shared between parties
- **Private Claims**: Custom application-specific claims

### JWT Security Best Practices
- Use RS256 or ES256 instead of HS256 for signing
- Never put sensitive information in JWT payload
- Validate JWT signature properly
- Implement token expiration checking
- Use proper token storage (HTTP-only cookies or secure storage)

## SAML (Security Assertion Markup Language)

### Introduction
SAML is an XML-based framework for exchanging authentication and authorization data between parties, particularly between an identity provider and a service provider.

### SAML Flows
#### Web Browser SSO Profile (IdP Initiated)
```
1. User initiates login at identity provider
2. IdP authenticates user
3. IdP generates SAML assertion
4. Browser posts assertion to service provider
5. SP validates assertion and grants access
```

#### Web Browser SSO Profile (SP Initiated)
```
1. User tries to access SP resource
2. SP redirects to IdP for authentication
3. IdP authenticates user
4. IdP generates SAML assertion
5. Browser posts assertion to SP
6. SP validates assertion and grants access
```

### SAML Security Considerations
- Validate SAML assertions properly
- Verify digital signatures
- Check certificate validity
- Prevent replay attacks with NotOnOrAfter
- Use proper binding methods (HTTP-POST preferred over HTTP-Redirect)

## LDAP (Lightweight Directory Access Protocol)

### Introduction
LDAP is an open, vendor-neutral, industry standard application protocol for accessing and maintaining distributed directory information services over an IP network.

### Common LDAP Operations
- **Bind**: Authenticate to the directory
- **Search**: Query directory entries
- **Add**: Create new directory entries
- **Modify**: Update existing entries
- **Delete**: Remove directory entries
- **Unbind**: Disconnect from directory

### LDAP Authentication Methods
- **Simple Authentication**: Plain text password
- **Simple Authentication with SSL**: Encrypted transmission
- **SASL Authentication**: External authentication services

### Active Directory Integration
Active Directory uses Microsoft's implementation of LDAP with additional extensions:
- Kerberos authentication support
- Group Policy Objects (GPOs)
- Domain Controller replication
- Global Catalog services

## Multi-Factor Authentication (MFA)

### Authentication Factors
- **Something you know**: Password, PIN
- **Something you have**: Hardware token, smartphone
- **Something you are**: Biometric data

### Common MFA Methods
#### Time-based One-Time Password (TOTP)
Based on RFC 6238, generates passwords synchronized with time:
```javascript
// TOTP calculation
function generateTOTP(secret, timeStep = 30) {
  const epoch = Math.floor(Date.now() / 1000);
  const counter = Math.floor(epoch / timeStep);
  const key = base32_decode(secret);
  const counterBytes = intToBytes(counter);
  const hmac = crypto.createHmac('sha1', key).update(counterBytes).digest();
  const offset = hmac[hmac.length - 1] & 0x0F;
  const binary = ((hmac[offset] & 0x7F) << 24) |
                 ((hmac[offset + 1] & 0xFF) << 16) |
                 ((hmac[offset + 2] & 0xFF) << 8) |
                 (hmac[offset + 3] & 0xFF);
  const otp = (binary % 1000000).toString().padStart(6, '0');
  return otp;
}
```

#### HMAC-based One-Time Password (HOTP)
Based on RFC 4226, generates passwords based on counter:
```
HOTP(K,C) = Truncate(HMAC-SHA-1(K,C))
```

#### SMS Authentication
Sends one-time passwords via SMS messages.

#### Push Notifications
Sends authentication requests to mobile applications for approval.

### MFA Security Considerations
- Use hardware tokens when possible
- Implement rate limiting for MFA attempts
- Provide backup authentication methods
- Protect against SIM swapping attacks
- Use push notifications over SMS when possible

## Session Management

### Session ID Generation
Generate cryptographically secure random session IDs:
```javascript
const crypto = require('crypto');

function generateSessionId() {
  return crypto.randomBytes(32).toString('hex');
}
```

### Session Storage Options
#### Server-side Storage
- Database storage (PostgreSQL, MySQL)
- In-memory storage (Redis, Memcached)
- File system storage

#### Client-side Storage
- Signed JWT tokens
- Encrypted tokens
- HTTP-only cookies

### Session Security Best Practices
- Use secure, HttpOnly, and SameSite attributes for cookies
- Implement session timeout and cleanup
- Regenerate session IDs after authentication
- Store minimal data in session
- Implement proper session invalidation
- Use SSL/TLS for all authenticated sessions

## Password Policies

### Complexity Requirements
- Minimum length (recommended: 12 characters)
- Mixed case letters (uppercase and lowercase)
- Numbers and special characters
- No common dictionary words
- No personal information patterns

### Password Storage
- Use bcrypt with cost factor ≥ 12
- Use Argon2 with appropriate parameters
- Implement proper salting (unique per password)
- Never store plaintext passwords

### Password History
- Remember last 24 passwords
- Prevent reuse of previous passwords
- Implement password aging policies
- Allow administrators to bypass history

## Single Sign-On (SSO)

### Benefits
- Reduced password fatigue
- Improved security posture
- Simplified user management
- Better compliance tracking

### Implementation Approaches
#### Federated SSO
- Centralized authentication authority
- Trust relationships between systems
- Shared identity attributes
- Common identity schema

#### Direct SSO
- Shared authentication mechanism
- Common password policy
- Centralized user management
- Unified user interface

### Security Considerations
- Protect the central authentication service
- Implement proper access controls
- Monitor for suspicious activities
- Plan for authentication service failures

## API Authentication

### Token-based Authentication
- OAuth 2.0 Bearer tokens
- API keys for machine-to-machine communication
- JWT tokens for stateless authentication
- Client certificates for high-security scenarios

### Rate Limiting
- Request counting and throttling
- Sliding window counters
- Different limits for authenticated vs. anonymous users
- Adaptive rate limiting based on user reputation

### Best Practices
- Use HTTPS for all API communications
- Implement proper error handling
- Avoid exposing sensitive information in headers
- Validate all API requests thoroughly
- Implement audit logging for API access

## Threat Modeling

### Common Authentication Threats
- Password guessing and brute force
- Session hijacking and fixation
- Token theft and replay
- Man-in-the-middle attacks
- Social engineering attacks

### Defense Strategies
- Multi-layered security controls
- Principle of least privilege
- Defense in depth approach
- Regular security assessments
- Incident response planning

### Security Controls
- Input validation and sanitization
- Output encoding and escaping
- Proper error handling
- Secure configuration management
- Regular security updates