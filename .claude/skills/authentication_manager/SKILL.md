# Authentication Manager Skill

## Purpose and Use Cases
The Authentication Manager skill provides comprehensive authentication and authorization capabilities for the Personal AI Employee system. It handles user registration, login, logout, password management, role-based access control, and secure session management. This skill ensures secure access to system resources and manages user identities across different services and applications.

## Input Parameters and Expected Formats
- `auth_action`: Authentication action ('register', 'login', 'logout', 'reset_password', 'change_password', 'verify_email', 'request_verification')
- `user_credentials`: User credentials (object with username/email and password)
- `user_profile`: User profile information for registration (object)
- `access_token`: Authentication token for protected operations (string)
- `refresh_token`: Refresh token for session renewal (string)
- `roles`: User roles for access control (array of strings)
- `permissions`: Specific permissions granted to user (array of strings)
- `auth_provider`: Authentication provider ('local', 'oauth_google', 'oauth_facebook', 'oauth_github')

## Processing Logic and Decision Trees
1. **User Registration**:
   - Validate user input and profile information
   - Hash and salt user password securely
   - Create user account in database
   - Generate verification token if required
   - Send welcome/verification email

2. **User Authentication**:
   - Validate user credentials against stored hash
   - Check account status and verification
   - Generate JWT access and refresh tokens
   - Set secure session cookies
   - Record authentication event

3. **Session Management**:
   - Validate and refresh tokens as needed
   - Manage token expiration and renewal
   - Track concurrent sessions
   - Handle session termination

4. **Authorization Checks**:
   - Verify user roles and permissions
   - Check resource access requirements
   - Enforce access control policies
   - Log authorization decisions

5. **Password Management**:
   - Handle password reset requests securely
   - Validate password strength requirements
   - Implement account lockout after failures
   - Manage password history to prevent reuse

6. **Multi-Factor Authentication**:
   - Generate and validate TOTP codes
   - Send SMS/app notification challenges
   - Manage backup authentication methods
   - Handle MFA enrollment and recovery

## Output Formats and File Structures
- Creates user accounts in /Data/users.db (SQLite database)
- Maintains authentication logs in /Logs/auth_events.log
- Stores encrypted tokens in /Security/tokens.dat
- Creates session files in /Sessions/[session_id].json
- Generates audit trails in /Audit/auth_audits_[date].log

## Error Handling Procedures
- Validate all authentication inputs to prevent injection
- Implement rate limiting for brute force protection
- Log authentication failures for security monitoring
- Alert administrators of suspicious activity
- Implement account lockout after repeated failures
- Handle token validation errors gracefully

## Security Considerations
- Use bcrypt or Argon2 for password hashing
- Implement secure token generation and storage
- Enforce HTTPS for all authentication operations
- Sanitize all user inputs to prevent injection
- Implement proper session cleanup and invalidation
- Use secure cookie attributes (HttpOnly, Secure, SameSite)

## Integration Points with Other System Components
- Integrates with Database Connector for user storage
- Connects with Email MCP for sending notifications
- Updates Dashboard Updater with authentication status
- Creates audit logs for Communication Logger
- Coordinates with Security Scanner for vulnerability checks