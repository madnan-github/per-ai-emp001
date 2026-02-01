# NextJS UI Builder Reference Guide

## Overview
The NextJS UI Builder skill provides comprehensive UI development capabilities for the Personal AI Employee system. It enables the creation, management, and deployment of modern NextJS user interfaces for dashboards, forms, and applications. This skill streamlines the development process by generating well-structured, accessible, and responsive UI components.

## Features and Capabilities

### Component Generation
- Create reusable React components with TypeScript support
- Generate common UI elements like buttons, cards, modals, and forms
- Implement proper accessibility attributes and keyboard navigation
- Support for dark/light mode themes
- Responsive design with mobile-first approach

### Page Creation
- Generate NextJS pages based on defined routing structures
- Implement server-side rendering (SSR) and static site generation (SSG) where appropriate
- Add metadata and SEO optimization for each page
- Create dynamic routes with proper parameter handling

### Styling Options
- Support for Tailwind CSS with custom configuration
- CSS Modules for scoped styling
- Styled Components for dynamic styling
- Emotion for advanced styling patterns
- Consistent design system implementation

### Data Integration
- Connect to various data sources (REST APIs, GraphQL, databases)
- Implement proper data fetching patterns (getServerSideProps, getStaticProps)
- Add error handling and loading states
- Optimize data loading for performance

### Authentication Setup
- Implement authentication flows (login, signup, password reset)
- Add protected routes and authorization
- Session management and security headers
- OAuth integration support

## Best Practices

### Component Architecture
- Follow the container/presentational pattern
- Implement proper prop drilling solutions
- Use Context API for global state management
- Leverage React hooks for state and side effects
- Create custom hooks for reusable logic

### Performance Optimization
- Implement code splitting with dynamic imports
- Optimize images with NextJS Image component
- Use lazy loading for non-critical components
- Implement proper caching strategies
- Minimize bundle size with tree shaking

### Accessibility
- Include proper ARIA attributes
- Implement keyboard navigation
- Ensure sufficient color contrast
- Provide alternative text for images
- Test with screen readers

### Security
- Sanitize user inputs to prevent XSS
- Implement proper CORS policies
- Use NextJS security headers
- Validate data on both client and server
- Protect against CSRF attacks

## Common UI Patterns

### Dashboard Layout
```
┌─────────────────────────────────┐
│ Header with navigation          │
├─────────────────────────────────┤
│ ┌───────┐ ┌──────────────────┐  │
│ │Sidebar│ │Main Content      │  │
│ │       │ │                  │  │
│ │       │ │                  │  │
│ │       │ │                  │  │
│ └───────┘ └──────────────────┘  │
└─────────────────────────────────┘
```

### Form Pattern
- Validation on submit and optionally on change
- Loading states during submission
- Success and error messaging
- Accessible form labels and descriptions

### Data Table Pattern
- Sorting and pagination
- Filtering and search capabilities
- Loading skeletons for better UX
- Export functionality

## File Structure
The generated NextJS application follows these conventions:

```
my-app/
├── components/           # Reusable UI components
│   ├── ui/             # Base UI components
│   ├── forms/          # Form components
│   └── layout/         # Layout components
├── pages/              # NextJS pages
│   ├── api/            # API routes
│   ├── _app.js         # Custom App component
│   ├── _document.js    # Custom Document component
│   └── index.js        # Home page
├── public/             # Static assets
├── styles/             # Global and utility styles
├── lib/                # Utility functions
└── utils/              # Helper functions
```

## Deployment Options

### Vercel (Recommended)
- Zero-config deployment for NextJS apps
- Automatic SSL certificates
- Global CDN distribution
- Preview deployments for pull requests

### Netlify
- Support for NextJS static exports
- Functions for server-side logic
- Form handling and identity services
- Split testing capabilities

### Custom Server
- Self-hosted deployment options
- Docker containerization support
- Reverse proxy configuration
- Load balancing capabilities

## Environment Variables
The skill uses these environment variables for configuration:

```
NEXT_PUBLIC_SITE_URL=https://yoursite.com
DATABASE_URL=postgresql://user:pass@localhost:5432/db
JWT_SECRET=your-jwt-secret
API_BASE_URL=https://api.yoursite.com
```

## Error Handling
The skill implements comprehensive error handling:

- Client-side error boundaries
- Server-side error logging
- Graceful degradation for failed operations
- User-friendly error messages
- Automated error reporting

## Testing Approach
- Unit tests for individual components
- Integration tests for component interactions
- End-to-end tests for critical user flows
- Visual regression testing for UI changes
- Accessibility testing with automated tools