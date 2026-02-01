# Bank Transaction Monitoring Rules

## Anomaly Detection Rules

### Amount-Based Anomalies
- **Unusual Large Transactions**: Transactions >3x average monthly spending
- **Small Test Charges**: Multiple charges <$5 within 24 hours (card testing)
- **Round Number Fraud**: Unnaturally round amounts like $100, $200 (possible fraud)
- **Missing Decimal Places**: Charges without cents portion (possible skimming)
- **Negative Amounts**: Unexpected credits or reversals

### Frequency-Based Anomalies
- **Spike Detection**: 3x higher transaction frequency than usual
- **Multiple Transactions**: More than 5 transactions from same merchant in 24 hours
- **Off-Hours Activity**: Transactions between 2AM-4AM when normally inactive
- **Consecutive Days**: Daily transactions when historically weekly/monthly
- **Burst Activity**: 10+ transactions in 1 hour (possible data breach)

### Location-Based Anomalies
- **Geographic Distance**: Transactions >100 miles from last known location
- **Impossible Travel**: Transactions in different countries in <24 hours
- **New Geographic Areas**: First-time transactions in new cities/countries
- **High-Risk Regions**: Transactions in known fraud hotspots
- **IP Address Mismatch**: Online transactions with suspicious IP addresses

## Categorization Rules

### Automatic Categorization
- **Merchant Name Matching**: Direct match to known merchant database
- **Description Keywords**: Pattern matching for common transaction types
- **Category Codes**: Use MCC (Merchant Category Codes) for classification
- **Amount Ranges**: Specific amounts tied to known subscription services
- **Recurring Pattern**: Similar amounts on regular intervals indicate subscriptions

### Business vs. Personal Classification
- **Time-Based**: Transactions during business hours likely business
- **Category-Based**: Office supplies, software, travel likely business
- **Amount Thresholds**: Transactions >$75 typically business (receipt required)
- **Merchant Classification**: B2B services classified as business
- **User Override**: Allow manual reclassification with approval

## Alert Thresholds

### Immediate Alerts (Within 1 Hour)
- **Suspicious Amounts**: Transactions >$500 if average is <$100
- **Geographic Anomalies**: International transactions if none expected
- **Multiple Declined**: 3+ declined transactions in 24 hours
- **Account Changes**: PIN changes, address updates, contact changes
- **New Cards**: Virtual card creation or new card requests

### Daily Summary Alerts
- **Spending Spikes**: Daily spending >2x average daily amount
- **Category Changes**: Significant shift in spending categories
- **New Merchants**: First-time transactions with unfamiliar vendors
- **Subscription Changes**: New recurring charges or changes to existing
- **Balance Anomalies**: Account balance <10% of typical range

### Weekly Summary Alerts
- **Trend Analysis**: Weekly spending compared to historical patterns
- **Budget Tracking**: Progress toward monthly budget goals
- **Investment Activity**: Significant investment transactions
- **Income Verification**: Confirmation of expected income receipts
- **Fee Monitoring**: Bank fees, overdrafts, ATM fees

## Approval Workflows

### High-Risk Transactions (Require Approval)
- **Amount Threshold**: Transactions >$1000 require approval
- **New Vendors**: First-time transactions with unknown merchants
- **International**: Cross-border transactions over $100
- **Business Expenses**: Business purchases over $500
- **Cash Withdrawals**: ATM withdrawals over $200

### Semi-Automated Transactions (Notification Only)
- **Medium Amounts**: Transactions $100-$1000
- **Category Changes**: Unexpected category classifications
- **Vendor Pattern Changes**: Different spending patterns with familiar vendors
- **Off-Hour Transactions**: After-hours business with non-24-hour merchants
- **Duplicate Charges**: Potential duplicate transactions

### Fully Automated (No Approval Needed)
- **Known Recurring**: Recognized subscription or bill payments
- **Small Amounts**: Transactions <$25
- **Low-Risk Categories**: Groceries, gas, utilities
- **Within Budget**: Transactions within established budget limits
- **Historical Patterns**: Following established spending patterns

## Fraud Prevention Rules

### Transaction Blocking
- **Known Fraudulent Merchants**: Block transactions with blacklisted vendors
- **Velocity Limits**: Maximum number of transactions per time period
- **Amount Caps**: Per-transaction and daily/monthly limits
- **Geographic Restrictions**: Block transactions from high-risk regions
- **Time Restrictions**: Limit transactions during unusual hours

### Enhanced Verification
- **Two-Factor Authentication**: SMS or app approval for high-value transactions
- **Biometric Verification**: Fingerprint or facial recognition for sensitive actions
- **Device Recognition**: Verify transaction device against known devices
- **Behavioral Analysis**: Flag deviations from normal spending patterns
- **Account Linking**: Verify linked account information matches

## Compliance Rules

### Regulatory Compliance
- **AML Requirements**: Anti-money laundering transaction monitoring
- **KYC Verification**: Know Your Customer validation requirements
- **Currency Reporting**: Report transactions over $10,000
- **Suspicious Activity**: Flag and report unusual transaction patterns
- **Record Keeping**: Maintain transaction records per regulatory requirements

### Internal Policies
- **Expense Policy**: Enforce company expense reimbursement policies
- **Authorization Limits**: Respect individual spending authorization limits
- **Receipt Requirements**: Mandate receipts for certain expense categories
- **Approval Chains**: Route approvals based on transaction amount/type
- **Audit Trails**: Maintain complete audit trails for all transactions

## Escalation Rules

### Level 1: Automated Response
- **Small Anomalies**: Send notification for review within 24 hours
- **Pattern Deviations**: Flag for manual review during business hours
- **New Categories**: Alert for new transaction categories
- **Minor Policy Violations**: Warning notifications for minor infractions

### Level 2: Manager Review
- **Moderate Risks**: Transactions between $500-$5000 with anomalies
- **Policy Violations**: Clear violations of expense policies
- **Recurring Issues**: Pattern of similar anomalies with same vendor
- **Category Disputes**: Disagreements about transaction categorization

### Level 3: Executive Approval
- **High-Value Transactions**: Transactions >$5000 with concerns
- **Major Policy Violations**: Serious breaches of financial policies
- **Potential Fraud**: Clear indicators of fraudulent activity
- **System Overrides**: Requests to bypass automated controls