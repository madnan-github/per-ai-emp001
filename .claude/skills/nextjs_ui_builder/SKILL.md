# NextJS UI Builder Skill

## Purpose and Use Cases
The NextJS UI Builder skill provides comprehensive UI development capabilities for the Personal AI Employee system. It creates, manages, and deploys NextJS user interfaces for dashboards, forms, and applications. This skill handles component generation, page creation, styling, routing, and deployment of NextJS applications to support the various business and personal tasks managed by the AI employee.

## Input Parameters and Expected Formats
- `ui_type`: Type of UI to create ('dashboard', 'form', 'landing_page', 'admin_panel', 'application')
- `components`: List of components to include in the UI (array of strings)
- `styling_framework`: Styling approach ('tailwind', 'css_modules', 'styled_components', 'emotion')
- `routing_structure`: Routing configuration (object with route definitions)
- `data_sources`: Data sources to connect to the UI (array of API endpoints or database connections)
- `authentication_required`: Whether authentication is needed (boolean)
- `responsive_design`: Whether responsive design is required (boolean)
- `deployment_target`: Where to deploy the UI ('vercel', 'netlify', 'custom_server')

## Processing Logic and Decision Trees
1. **UI Planning**:
   - Analyze UI requirements and structure
   - Select appropriate components and layouts
   - Define styling and responsive behavior
   - Plan data integration approach

2. **Component Generation**:
   - Create reusable UI components
   - Implement proper TypeScript typing
   - Add accessibility features
   - Ensure responsive design

3. **Page Creation**:
   - Generate NextJS pages based on routing structure
   - Implement server-side rendering where appropriate
   - Add metadata and SEO optimization
   - Create dynamic routes as needed

4. **Styling Implementation**:
   - Apply selected styling framework
   - Create consistent design system
   - Implement dark/light mode if required
   - Optimize for performance

5. **Data Integration**:
   - Connect to specified data sources
   - Implement API routes or data fetching
   - Add error handling for data operations
   - Optimize data loading patterns

6. **Authentication Setup**:
   - Implement authentication if required
   - Add protected routes
   - Set up session management
   - Configure security headers

7. **Deployment Preparation**:
   - Optimize build configuration
   - Set up environment variables
   - Prepare for specified deployment target
   - Run build process

## Output Formats and File Structures
- Creates UI components in /components/[ui_name]/[component].tsx
- Generates pages in /pages/ or /app/ based on NextJS version
- Creates API routes in /pages/api/ or /app/api/
- Sets up styling in /styles/ or using framework-specific approach
- Generates configuration files (next.config.js, tsconfig.json if needed)
- Creates deployment configuration for specified target

## Error Handling Procedures
- Validate component props and data structures
- Handle API errors gracefully with fallbacks
- Implement proper error boundaries
- Log UI errors to /Logs/ui_builder_errors.log
- Rollback deployment if build fails
- Validate responsive behavior across devices

## Security Considerations
- Sanitize all user-generated content in templates
- Implement proper CORS policies
- Use NextJS security headers
- Validate and sanitize form inputs
- Implement proper authentication flows
- Protect against XSS and CSRF attacks

## Integration Points with Other System Components
- Integrates with Database Connector for data storage
- Connects with API Gateway for backend communication
- Updates Dashboard Updater with UI status
- Creates audit logs for Communication Logger
- Coordinates with Deployment Manager for publishing