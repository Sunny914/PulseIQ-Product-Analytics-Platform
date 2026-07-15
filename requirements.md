# Product Analytics Platform Requirements

## 1. Objective

The system must ingest source operational data for a SaaS CRM-style business and produce a medallion-layer analytics dataset that can be consumed by BI tools, especially Power BI.

The implementation must support reporting on account health, user activity, product engagement, pipeline performance, and activation behavior.

## 2. Scope

### 2.1 In-Scope Data Sources

The project must support the following raw source domains:

- Accounts
- Users
- Deals
- Product events
- Geography

### 2.2 In-Scope Output Layers

The solution must produce the following layers:

1. Bronze layer for raw ingestion
2. Silver layer for cleaning, standardization, and enrichment
3. Gold layer for analytics-ready dimensions and facts
4. CSV exports for downstream BI consumption

## 3. Functional Requirements

### FR1. Bronze Layer Ingestion

The bronze layer must load the raw source tables directly from the source system into DuckDB tables without applying business logic.

Required bronze outputs:

- `bronze_accounts`
- `bronze_users`
- `bronze_deals`
- `bronze_product_events`
- `bronze_geography`

### FR2. Silver Account Standardization

The `silver_accounts` table must:

- normalize account name, country code, segment, and acquisition channel values
- enrich accounts with geography fields from the geography lookup
- convert `created_at` to `created_date`
- compute `account_age_days` using the current date and account creation date
- assign `account_age_bucket` with the following business thresholds:
  - `<30 days`
  - `30-89 days`
  - `90-179 days`
  - `180+ days`
- calculate `trial_length_days` when both trial start and trial end dates are present
- derive `is_active_account` from `account_status = 'active'`
- derive `has_trial` when a trial start date exists

### FR3. Silver User Standardization

The `silver_users` table must:

- preserve `user_id` and `account_id`
- derive `email_domain` from the email address
- convert `created_at` to `created_date`
- compute `user_tenure_days` using account creation date and current date
- compute `days_since_last_seen` when `last_seen_at` is present
- assign `recency_bucket` with the following business thresholds:
  - `<7 days`
  - `7-29 days`
  - `30-89 days`
  - `90+ days`
- derive `is_active_user` from `user_status = 'active'`

### FR4. Silver Deal Standardization

The `silver_deals` table must:

- normalize `status` to lowercase text
- normalize `currency` and `country_code` to uppercase
- convert timestamps to date fields
- identify `is_closed` when `closed_at` is present
- identify `is_won` when the status is `won` or `closed_won`
- compute `deal_cycle_days` when the deal is closed
- compute `deal_age_days` using deal creation date and current date

### FR5. Silver Product Event Standardization

The `silver_product_events` table must:

- exclude `is_test_event = FALSE` records from the bronze table
- normalize `country_code` to uppercase
- derive `event_ts_date` and `event_ts_month` from the event timestamp
- classify each event into one of the following categories:
  - `AUTH`
  - `PIPELINE`
  - `ACTIVITY`
  - `AUTOMATION`
  - `OTHER`
- set `has_deal_context = TRUE` when a valid `deal_id` exists

### FR6. Silver Geography Deduplication

The `silver_geography` table must:

- standardize `country_code` to uppercase
- remove duplicate rows by `country_code`
- retain one geography row per country code
- handle the `UK` market override requirement where the market is null and the country code is `UK`

### FR7. Gold Dimension Tables

The gold layer must produce the following dimension tables:

- `gold_dim_accounts`
- `gold_dim_users`
- `gold_dim_geography`

These tables must expose the cleaned, business-ready attributes needed for downstream reporting and segmentation.

### FR8. Gold Fact Tables

The gold layer must produce the following fact tables:

- `gold_fact_deals`
- `gold_fact_product_events`
- `gold_fact_product_events_aggregated`
- `gold_fact_advanced_activation`

### FR9. Aggregated Product Event Fact

The `gold_fact_product_events_aggregated` table must summarize product events by:

- `EventDate`
- `EventName`
- `EventCategory`
- `AccountId`

The aggregation must include:

- total event count
- distinct user count per event group

### FR10. Advanced Activation Requirement

The `gold_fact_advanced_activation` table must define activation using a business rule based on account activity within the first 14 days after account creation.

An account is considered activated only when both of the following conditions are met:

1. At least one core product event with deal context occurs during the first 14 days
2. At least one deal is created during the first 14 days

The implementation must output the following fields:

- `AccountId`
- `CreatedDate`
- `FirstCoreEventDate`
- `FirstDealDate`
- `ActivationDate`
- `IsActivated`
- `TimeToValueDays`
- `CoreEventsInFirst14Days`
- `DealsInFirst14Days`

### FR11. CSV Export Requirement

The project must export the gold tables to CSV format so they can be consumed by Power BI and other reporting tools.

Required export files:

- `gold_dim_accounts.csv`
- `gold_dim_geography.csv`
- `gold_dim_users.csv`
- `gold_fact_advanced_activation.csv`
- `gold_fact_deals.csv`
- `gold_fact_product_events.csv`
- `gold_fact_product_events_aggregated.csv`

## 4. Non-Functional Requirements

### NFR1. Reproducibility

Running the transformation scripts on the same source data must produce the same analytical outputs.

### NFR2. Local Analytics Workflow

The project must be runnable in a local development environment using DuckDB and Python-based SQL transformation scripts.

### NFR3. Maintainability

The code must be organized by layer so the bronze, silver, and gold logic can be updated independently.

### NFR4. BI Readiness

The gold outputs must be structured to support reporting, KPI analysis, and dashboard development.

## 5. Acceptance Criteria

The requirements are satisfied when:

- all five bronze tables exist and mirror the source schema
- the silver layer standardizes and enriches account, user, deal, event, and geography records
- the gold layer contains the expected dimensions and facts
- `gold_fact_advanced_activation` implements the 14-day activation logic
- all required gold tables are exported to CSV format
- the resulting dataset is suitable for Power BI and product analytics reporting
