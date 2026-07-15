# 🚀 SaaS Product Analytics Platform

> Built to simulate the analytics stack of a modern B2B SaaS company and demonstrate production-style data modeling, KPI engineering, product analytics workflows, and analytics engineering practices used by Product Analysts, Data Analysts, and Analytics Engineers.

---

## 📌 Project Overview

This project recreates the internal analytics platform of a SaaS CRM business similar to Salesforce, HubSpot, or Zoho CRM.

The objective is to transform raw operational data into business-ready insights that can be consumed by Product, Sales, Growth, Customer Success, and Executive teams.

Unlike traditional dashboard projects, this repository demonstrates the complete analytics lifecycle:

- Data ingestion
- Data cleaning and standardization
- Data enrichment
- Dimensional modeling
- Fact table creation
- KPI engineering
- Product activation modeling
- Dashboard-ready semantic layer creation

---

## 🏗 Architecture

This project follows the **Medallion Architecture** approach:

```text
Raw Data Sources
        │
        ▼
┌──────────────────┐
│ Bronze Layer     │
│ Raw ingestion    │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Silver Layer     │
│ Cleaning         │
│ Validation       │
│ Standardization  │
│ Enrichment       │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Gold Layer       │
│ Dimensions       │
│ Facts            |
| Measures         │
│ KPIs             │
│ Business Metrics │
└──────────────────┘
        │
        ▼
Power BI Dashboards
```

---

# 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| Database | DuckDB |
| Query Engine | SQL |
| Transformation | SQL + Python |
| Analytics | Power BI |
| Data Processing | Pandas |
| Data Modeling | Star Schema |
| Architecture | Medallion Architecture |
| Version Control | Git + GitHub |

---

# 📂 Repository Structure

```text
SaaS_Product_Analytics/
│
├── data/
│
├── sql/
│   │
│   ├── bronze/
│   │   ├── bronze_accounts.py
│   │   ├── bronze_users.py
│   │   ├── bronze_deals.py
│   │   ├── bronze_product_events.py
│   │   └── bronze_geography.py
│   │
│   ├── silver/
│   │   ├── silver_accounts.py
│   │   ├── silver_users.py
│   │   ├── silver_deals.py
│   │   ├── silver_product_events.py
│   │   └── silver_geography.py
│   │
│   └── gold/
│       ├── gold_dim_accounts.py
│       ├── gold_dim_users.py
│       ├── gold_dim_geography.py
│       ├── gold_fact_deals.py
│       ├── gold_fact_product_events.py
│       ├── gold_fact_product_events_aggregated.py
│       └── gold_fact_advanced_activation.py
│
├── presentations/
│
├── assets/
│
├── product_analytics_light.db
│
└── README.md
```

---

# 🏢 Business Scenario

Assume a SaaS CRM company wants to answer questions such as:

- Which acquisition channels generate the highest quality customers?
- Which regions generate the highest revenue?
- How long does it take customers to reach activation?
- Which features drive customer adoption?
- Which segments produce the largest deals?
- What impacts customer conversion and retention?

This analytics platform is designed to answer those questions.

---

# ⭐ Medallion Layers

## 🥉 Bronze Layer

Raw source data ingested directly into DuckDB without transformations.

Examples:

- Accounts
- Users
- Deals
- Product Events
- Geography

---

## 🥈 Silver Layer

Business-ready cleaned tables containing:

- Standardized text values
- Date conversions
- Derived fields
- Data quality improvements
- Enrichment joins

Examples:

- Account age calculation
- Trial length calculation
- User tenure calculation
- Geographic enrichment

---

## 🥇 Gold Layer

Analytics-ready dimensional models optimized for BI reporting and stakeholder consumption.

Contains:

- Dimension tables
- Fact tables
- Business KPIs
- Product metrics
- Revenue metrics

---

# 📊 Data Model

## Dimension Tables

### `gold_dim_accounts`

Contains account-level business information.

Features:

- Industry
- Segment
- Employee Band
- Acquisition Channel
- Trial Information
- Geography
- Account Age Metrics

---

### `gold_dim_users`

Contains user-level attributes.

Features:

- User Role
- User Status
- User Tenure
- Recency Bucket
- Admin Flag

---

### `gold_dim_geography`

Contains geographical hierarchy information.

Features:

- Country
- Region
- Market
- Sales Region
- Currency

---

## Fact Tables

### `gold_fact_product_events`

Stores all user interactions with the product.

Examples:

- Login events
- Feature usage
- Pipeline interactions
- Deal interactions

---

### `gold_fact_deals`

Stores CRM pipeline activity.

Metrics include:

- Deal Value
- Pipeline Stage
- Deal Cycle Length
- Win Status
- Deal Age

---

### `gold_fact_product_events_aggregated`

Daily aggregation table for product analytics reporting.

Used for:

- DAU
- Feature Adoption
- Usage Trends
- Event Tracking

---

### `gold_fact_advanced_activation`

Custom activation framework inspired by modern SaaS businesses.

Activation requires:

✅ Product engagement

AND

✅ Evidence of business workflow adoption

Specifically:

- Core product usage
- Deal or pipeline activity

This provides a far stronger activation signal than simple login activity.

---

# 📈 KPIs and Metrics

## Growth Metrics

- New Accounts
- New Users
- Signup Growth Rate
- Trial Conversion Rate

---

## Product Metrics

- DAU-Daily Active Users
- WAU-Weekly Active Users
- MAU-Monthly Active Users
- Feature Adoption Rate
- Engagement Rate

---

## Revenue Metrics

- Pipeline Value
- Average Deal Size
- Win Rate
- Deal Velocity

---

## Customer Metrics

- Activation Rate
- Time To Value
- Customer Segmentation
- Regional Distribution

---

# 🧠 Advanced Analytics Concepts Demonstrated

This project demonstrates knowledge of:

- Medallion Architecture
- Star Schema Design
- Dimensional Modeling
- Product Analytics
- Behavioral Analytics
- Activation Frameworks
- Revenue Analytics
- KPI Engineering
- Analytics Engineering
- Business Intelligence

---

# 📊 Example Business Questions Answered

## Product Team

- Which features correlate with activation?
- Which users become power users?

## Sales Team

- Which acquisition channels produce larger deals?
- What is the average deal cycle duration?

## Growth Team

- Which segments activate fastest?
- Which geographies convert best?

## Leadership Team

- What drives revenue growth?
- Where should investment be focused?

---

# 📷 Dashboard Preview

## Executive Overview Dashboard

![Executive Overview](presentations/executive_overview.jpg)

---

## Product Adoption Dashboard

![Product Usage Dashboard](presentations/product_usage_adoption.jpg)

---

## Activation Time-To-Value Analytics Dashboard

![Activation Dashboard](presentations/activation_time_to_value.jpg)

---

## Activation Funnel Dashboard

![Activation Funnel Dashboard](presentations/activation_funnel_health_monitoring.jpg)
---

# 🎯 Skills Demonstrated

## Data Analytics

- SQL
- Data Cleaning
- Exploratory Data Analysis
- KPI Design
- Dashboard Development

---

## Analytics Engineering

- ETL Development
- Data Transformation
- Dimensional Modeling
- Medallion Architecture

---

## Product Analytics

- Activation Metrics
- Funnel Analysis
- User Behavior Analysis
- Event Analytics

---

## Business Intelligence

- Power BI
- DAX
- Executive Reporting
- Stakeholder Communication

---

# 🚀 Why This Project Matters

Most analytics portfolios contain:

- Superstore datasets
- Basic dashboards
- Simple visualizations

This project goes significantly further by demonstrating the ability to:

- Design analytics systems
- Model business entities
- Engineer KPIs
- Build product metrics
- Support executive decision making

The workflow closely resembles the analytics infrastructure used inside modern SaaS companies.

---

# 👨‍💻 Author

**Sunny**

Final Year Engineering Student  
Aspiring Data Analyst | Product Analyst | Analytics Engineer

Interested in:

- Product Analytics
- Data Analytics
- Business Intelligence
- Analytics Engineering
- Data Engineering

---

## ⭐ If you found this project useful, consider giving it a star.