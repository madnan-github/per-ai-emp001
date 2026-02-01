# Security Scanner Skill

## Purpose and Use Cases
The Security Scanner skill provides comprehensive security scanning and vulnerability assessment for the Personal AI Employee system. It performs automated security checks, vulnerability scanning, compliance auditing, and threat detection across system components, files, configurations, and network connections. This skill ensures the security posture of the system remains strong and compliant with security standards.

## Input Parameters and Expected Formats
- `scan_type`: Type of security scan ('vulnerability', 'configuration', 'file_integrity', 'network', 'compliance')
- `target`: Target for scanning (file path, directory, IP address, URL, or 'system')
- `scan_depth`: Depth of scan ('basic', 'standard', 'deep', 'comprehensive')
- `compliance_standard`: Compliance standard to check ('nist', 'iso27001', 'sox', 'gdpr', 'hipaa')
- `severity_threshold`: Minimum severity to report ('low', 'medium', 'high', 'critical')
- `scan_schedule`: Schedule for recurring scans (cron format)
- `exclude_patterns`: Patterns to exclude from scan (list of strings)
- `report_format`: Format for security reports ('json', 'csv', 'html', 'pdf')

## Processing Logic and Decision Trees
1. **Asset Discovery**:
   - Identify system assets and components
   - Map network topology and connections
   - Catalog installed software and versions
   - Inventory system configurations

2. **Vulnerability Scanning**:
   - Scan for known vulnerabilities
   - Check for outdated software versions
   - Identify misconfigurations
   - Assess security patch levels

3. **Compliance Checking**:
   - Validate against compliance standards
   - Check security policy adherence
   - Verify access controls and permissions
   - Audit security configurations

4. **Threat Detection**:
   - Scan for malware and suspicious files
   - Detect anomalous network traffic
   - Identify unauthorized access attempts
   - Monitor for suspicious activities

5. **Risk Assessment**:
   - Evaluate identified vulnerabilities
   - Calculate risk scores and impact
   - Prioritize remediation efforts
   - Generate security recommendations

## Output Formats and File Structures
- Creates security reports in /Reports/security_scan_[timestamp].[format]
- Updates security dashboard in /Dashboard/security_status.md
- Maintains vulnerability database in /Data/vulnerabilities.db
- Generates compliance reports in /Reports/compliance_[standard]_[date].md
- Creates security alerts in /Alerts/security_[timestamp].txt

## Error Handling Procedures
- Retry failed security scans with exponential backoff
- Alert if critical vulnerabilities are detected
- Implement circuit breaker for overloaded scanners
- Log scanning errors to /Logs/security_scanner_errors.log
- Route critical security findings to /Pending_Approval/ for immediate attention

## Security Considerations
- Validate all scan targets to prevent path traversal
- Implement safe scanning practices to avoid system disruption
- Maintain detailed audit trail of all security scans
- Secure scan results and vulnerability data
- Protect against scan-based reconnaissance

## Integration Points with Other System Components
- Integrates with all other skills for security scanning
- Connects with Error Handler for scanning-related errors
- Updates Dashboard Updater with security metrics
- Creates audit logs for Communication Logger
- Coordinates with Scheduler for recurring scans