# Authentication Manager Reference Guide

## Overview
The Authentication Manager skill provides comprehensive authentication and authorization capabilities for the Personal AI Employee system. It handles user registration, login, logout, password management, role-based access control, and secure session management. This skill ensures secure access to system resources and manages user identities across different services and applications.

## Features and Capabilities

### User Management
- User registration with email verification
- Secure login/logout functionality
- Password reset and change operations
- Account activation/deactivation
- User profile management
- Multi-factor authentication (MFA)

### Authentication Methods
- Local username/password authentication
- OAuth 2.0 integration (Google, Facebook, GitHub)
- JWT (JSON Web Token) based authentication
- Session-based authentication
- API key authentication
- Certificate-based authentication

### Authorization Controls
- Role-based access control (RBAC)
- Permission-based access control
- Attribute-based access control (ABAC)
- Time-based access restrictions
- IP-based access controls
- Device-based access controls

### Security Features
- Password strength enforcement
- Account lockout after failed attempts
- Secure password reset with time-limited tokens
- Session timeout and cleanup
- Brute force attack prevention
- Secure token generation and validation

## Architecture

### Authentication Flow
```
Client -> Authentication Manager -> Identity Provider
   |                                    |
   | (credentials)                      | (token/validation)
   |                                    |
   v                                    v
Validation -> Token Generation -> Response
```

### Component Architecture
- **User Service**: Manages user data and profiles
- **Authentication Service**: Handles login/logout operations
- **Authorization Service**: Manages roles and permissions
- **Token Service**: Handles JWT generation and validation
- **Session Service**: Manages active sessions
- **Audit Service**: Logs authentication events

## Security Best Practices

### Password Security
- Use bcrypt or Argon2 for password hashing
- Enforce strong password policies:
  - Minimum 12 characters
  - Mixed case letters
  - Numbers and special characters
  - No common dictionary words
- Implement password history to prevent reuse
- Use salting to prevent rainbow table attacks

### Token Security
- Use JWT with RS256 algorithm for signing
- Implement short-lived access tokens (15-30 minutes)
- Use longer-lived refresh tokens (7-30 days)
- Store tokens securely (HTTP-only cookies or secure storage)
- Implement token blacklisting for logout
- Use secure random generators for token creation

### Session Management
- Generate cryptographically secure session IDs
- Implement session timeout (15-30 minutes of inactivity)
- Regenerate session IDs after login
- Store session data server-side
- Implement concurrent session limits
- Clean up expired sessions automatically

### Input Validation
- Validate all user inputs on both client and server
- Sanitize inputs to prevent injection attacks
- Use parameterized queries to prevent SQL injection
- Implement CSRF protection with tokens
- Validate file uploads and content types
- Use content security policy headers

## Implementation Patterns

### JWT Authentication Pattern
```javascript
// Generate JWT token
function generateToken(user) {
  const payload = {
    userId: user.id,
    email: user.email,
    roles: user.roles,
    exp: Math.floor(Date.now() / 1000) + (60 * 15) // 15 minutes
  };

  return jwt.sign(payload, process.env.JWT_SECRET, {
    algorithm: 'RS256'
  });
}

// Verify JWT token
function verifyToken(token) {
  try {
    return jwt.verify(token, process.env.JWT_PUBLIC_KEY, {
      algorithms: ['RS256']
    });
  } catch (error) {
    throw new AuthenticationError('Invalid token');
  }
}
```

### Role-Based Access Control (RBAC)
```javascript
// Check user permissions
function checkPermission(user, resource, action) {
  const userRoles = user.roles;
  const requiredPermissions = getResourcePermissions(resource, action);

  return userRoles.some(role =>
    hasRolePermission(role, requiredPermissions)
  );
}

// Middleware for authorization
function requirePermission(resource, action) {
  return (req, res, next) => {
    const user = req.user;

    if (!checkPermission(user, resource, action)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }

    next();
  };
}
```

### Password Reset Flow
```
1. User requests password reset
2. System generates time-limited token
3. Token sent to user's registered email
4. User clicks link with token
5. System validates token and allows new password
6. Token is invalidated after use
7. User logs in with new password
```

## API Endpoints

### Authentication Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Token refresh
- `POST /auth/forgot-password` - Password reset request
- `POST /auth/reset-password` - Password reset confirmation

### User Management Endpoints
- `GET /users/profile` - Get user profile
- `PUT /users/profile` - Update user profile
- `POST /users/change-password` - Change password
- `POST /users/verify-email` - Email verification
- `POST /users/enable-mfa` - Enable multi-factor auth
- `POST /users/disable-mfa` - Disable multi-factor auth

### Admin Endpoints
- `GET /admin/users` - List users
- `PUT /admin/users/:id` - Update user (admin)
- `DELETE /admin/users/:id` - Deactivate user
- `POST /admin/users/:id/lock` - Lock user account
- `POST /admin/users/:id/unlock` - Unlock user account

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  salt VARCHAR(255),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  phone VARCHAR(20),
  is_active BOOLEAN DEFAULT TRUE,
  is_verified BOOLEAN DEFAULT FALSE,
  email_verified_at TIMESTAMP,
  password_reset_token VARCHAR(255),
  password_reset_expires TIMESTAMP,
  failed_login_attempts INTEGER DEFAULT 0,
  locked_until TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Roles Table
```sql
CREATE TABLE roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User Roles Junction Table
```sql
CREATE TABLE user_roles (
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
  assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, role_id)
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token VARCHAR(512) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Error Handling

### Common Error Codes
- `AUTH_001`: Invalid credentials
- `AUTH_002`: Account locked
- `AUTH_003`: Account not verified
- `AUTH_004`: Token expired
- `AUTH_005`: Token invalid
- `AUTH_006`: Insufficient permissions
- `AUTH_007`: Rate limit exceeded
- `AUTH_008`: Password too weak
- `AUTH_009`: Account already exists
- `AUTH_010`: Invalid token for password reset

### Error Response Format
```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid email or password",
    "details": "The provided credentials do not match our records"
  }
}
```

## Security Headers

### Recommended HTTP Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Rate Limiting

### Implementation Approaches
1. **Token Bucket Algorithm**: Allows bursts within limits
2. **Leaky Bucket Algorithm**: Smooths request rate
3. **Fixed Window Counter**: Simple counter per time window
4. **Sliding Window Log**: Tracks timestamps for precision

### Rate Limits by Endpoint
- Login attempts: 5 per 15 minutes per IP
- Registration: 1 per hour per IP
- Password reset: 3 per hour per email
- Token refresh: 10 per minute per user
- Account verification: 5 per day per email

## Audit Logging

### Events to Log
- Successful/failed login attempts
- Password changes
- Account lockouts/unlocks
- Role/permission changes
- Session creation/destruction
- Password reset requests
- MFA enrollment/disabling

### Audit Log Format
```
[timestamp] [user_id|anonymous] [ip_address] [action] [result] [details]
```

Example:
```
2026-02-01T10:30:45Z user_123 192.168.1.100 login success email:user@example.com
2026-02-01T10:31:22Z anonymous 192.168.1.100 login failure email:test@example.com
```

## Testing Strategies

### Unit Tests
- Password hashing and verification
- Token generation and validation
- Permission checking logic
- Input validation functions
- Error handling paths

### Integration Tests
- Complete authentication flows
- Database operations
- Third-party service integrations
- Session management
- Authorization middleware

### Security Tests
- Injection attack prevention
- Session hijacking attempts
- Token manipulation
- Privilege escalation
- Rate limiting effectiveness

## Performance Considerations

### Caching Strategies
- Cache user roles and permissions
- Cache JWT public keys
- Cache frequently accessed user data
- Use Redis for distributed session storage
- Cache authentication results temporarily

### Database Optimization
- Index email and username fields
- Partition audit logs by date
- Use connection pooling
- Optimize queries for user lookup
- Consider read replicas for authentication

### Scalability Patterns
- Stateless authentication with JWT
- Distributed session storage
- Load balancing for authentication services
- Horizontal scaling of authentication nodes
- CDN for static authentication assets