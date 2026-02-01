# Bank Transaction Categories

## Standard Categories

### Income Categories
- **Salary/Wages**: Regular employment income
- **Freelance Income**: Independent contractor payments
- **Investment Income**: Dividends, interest, capital gains
- **Business Revenue**: Sales and service revenue
- **Rental Income**: Property rental payments
- **Government Benefits**: Unemployment, disability, social security
- **Tax Refunds**: Federal, state, or local tax refunds

### Expense Categories
- **Rent/Mortgage**: Housing payments
- **Utilities**: Electricity, gas, water, internet, phone
- **Groceries**: Food and household essentials
- **Dining Out**: Restaurants and food delivery
- **Transportation**: Gas, public transit, ride-sharing, vehicle payments
- **Healthcare**: Medical bills, insurance, prescriptions
- **Insurance**: Health, auto, home, life insurance
- **Entertainment**: Movies, games, streaming services
- **Travel**: Flights, hotels, car rentals, attractions
- **Shopping**: Retail purchases, clothing, electronics
- **Education**: Tuition, books, supplies, courses
- **Charitable Giving**: Donations to nonprofits
- **Business Expenses**: Office supplies, software, travel, meals
- **Professional Services**: Legal, accounting, consulting

## Transaction Subcategories

### Income Subcategories
- **Primary Employment**: Main job salary
- **Secondary Employment**: Part-time job income
- **Contract Work**: Freelance or gig work
- **Investment Gains**: Stocks, bonds, real estate
- **Interest Income**: Bank accounts, CDs, bonds
- **Dividend Income**: Stock dividends
- **Royalties**: Intellectual property payments
- **Side Business**: Additional business income

### Fixed Expenses
- **Mortgage Payment**: Principal and interest
- **Property Tax**: Real estate taxes
- **Home Insurance**: Homeowners insurance
- **Auto Loan**: Vehicle financing
- **Life Insurance**: Life insurance premiums
- **Health Insurance**: Medical insurance premiums
- **Child Care**: Daycare or nanny services

### Variable Expenses
- **Fuel**: Gasoline, diesel, electric charging
- **Maintenance**: Vehicle repairs, home maintenance
- **Medical**: Doctor visits, prescriptions, procedures
- **Personal Care**: Haircuts, cosmetics, toiletries
- **Subscriptions**: Streaming, magazines, software
- **Gifts**: Birthday, holiday, wedding gifts
- **Pet Care**: Food, vet bills, grooming

## Business Categories

### Revenue Categories
- **Product Sales**: Physical goods sold
- **Service Revenue**: Consulting, professional services
- **Subscription Revenue**: Recurring membership fees
- **Licensing Fees**: IP licensing income
- **Commissions**: Sales commissions
- **Grants**: Government or foundation grants

### Business Expense Categories
- **Office Supplies**: Paper, pens, equipment
- **Software Licenses**: Business software subscriptions
- **Marketing**: Advertising, SEO, social media ads
- **Professional Services**: Legal, accounting, consulting
- **Equipment**: Computers, furniture, machinery
- **Facilities**: Rent, utilities, maintenance
- **Payroll**: Salaries, benefits, payroll taxes
- **Travel**: Business trips, conferences, meetings
- **Meals**: Client entertainment, business lunches
- **Insurance**: Business liability, property insurance

## Anomaly Detection Categories

### Suspicious Transactions
- **Unusual Amount**: Transactions significantly different from norm
- **Unusual Time**: Transactions outside normal hours
- **Unusual Location**: Transactions in unexpected geographic areas
- **Frequent Small**: Multiple small transactions to avoid detection
- **Round Numbers**: Unnaturally round amounts that may indicate fraud
- **Card Testing**: Multiple small transactions to test card validity
- **Reversed Charges**: Previously authorized charges reversed

### Potential Fraud Indicators
- **Duplicate Charges**: Same merchant, amount, and time
- **Unauthorized Charges**: Transactions at unknown merchants
- **ATM Fees**: Unexpected ATM fees from unknown locations
- **Foreign Transactions**: International charges not recognized
- **Chargebacks**: Customer-initiated reversals
- **Returned Items**: Merchandise returns causing reversals

## Personal Finance Categories

### Savings Categories
- **Emergency Fund**: Emergency reserve contributions
- **Retirement**: 401(k), IRA, pension contributions
- **Investment**: Brokerage account deposits
- **Vacation Fund**: Vacation savings
- **Major Purchase**: Car, house, education savings
- **General Savings**: General savings account deposits

### Debt Categories
- **Credit Card Payments**: Credit card balance payments
- **Student Loans**: Student loan payments
- **Personal Loans**: Personal loan payments
- **Mortgage Payments**: Principal and interest payments
- **Auto Loans**: Vehicle loan payments
- **Line of Credit**: HELOC or other credit line payments

## Seasonal Categories

### Holiday Spending
- **Holiday Gifts**: Christmas, birthday, anniversary gifts
- **Holiday Travel**: Vacation travel during holidays
- **Holiday Entertainment**: Holiday parties, decorations
- **Back to School**: Educational supplies and clothing

### Annual Events
- **Tax Preparation**: Annual tax preparation fees
- **Annual Subscriptions**: Yearly subscription renewals
- **Insurance Renewals**: Annual insurance premium payments
- **Membership Fees**: Annual club or gym memberships

## Category Assignment Rules

### Priority Rules
1. **Business vs. Personal**: If dual-use, split between categories
2. **Time-Based**: Business use during work hours, personal otherwise
3. **Amount Threshold**: Business expenses over $75 require receipts
4. **Merchant Classification**: Use merchant category codes as primary guide

### Split Transaction Rules
- **Mixed Purchases**: Separate food from non-food items when possible
- **Business Meals**: 50% business, 50% personal for mixed business/personal meals
- **Dual-Purpose Items**: Allocate based on primary use
- **Shared Expenses**: Split equally among users unless specified otherwise