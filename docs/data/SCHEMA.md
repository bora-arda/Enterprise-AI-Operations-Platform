# Database Schema

## Overview

The database uses PostgreSQL with the pgvector extension for vector search. All tables use UUID primary keys and include audit timestamps.

## Entity-Relationship Diagram

See the [DESIGN.md](../../architecture/DESIGN.md#g-database-schema) for the full ER diagram.

## Table Summaries

### Core Entities

| Table | Purpose | Key Columns |
|---|---|---|
| `buyers` | Public sector buying organizations | name, country, identifier |
| `vendors` | Suppliers/contractors | name, tax_id, country, status |
| `contracts` | Procurement contracts | contract_number, vendor_id, value, max_value, currency, status |
| `purchase_orders` | Purchase orders | po_number, contract_id, vendor_id, total_amount, status |
| `purchase_order_items` | PO line items | po_id, description, quantity, unit_price |
| `invoices` | Invoices | invoice_number, po_id, vendor_id, amount, status, payment_status |
| `invoice_items` | Invoice line items | invoice_id, description, quantity, unit_price |
| `payments` | Payment records | payment_reference, invoice_id, amount, status |

### Workflow Entities

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | System users | name, email, role, department_id |
| `departments` | Organizational departments | name, code, budget_limit |
| `approval_requests` | Approval workflow requests | request_type, invoice_id, status |
| `exceptions` | Detected exceptions/anomalies | invoice_id, exception_type, severity, status |

### Audit & Observability

| Table | Purpose | Key Columns |
|---|---|---|
| `audit_logs` | Audit trail | user_id, action, entity_type, entity_id, details |
| `procurement_events` | Operational events | event_type, entity_type, entity_id, details |

### Vector Store

| Table | Purpose | Key Columns |
|---|---|---|
| `documents` | Embedded document chunks | document_id, document_type, content, embedding, metadata |

## Indexes

```sql
-- Foreign key indexes
CREATE INDEX idx_contracts_vendor_id ON contracts(vendor_id);
CREATE INDEX idx_purchase_orders_contract_id ON purchase_orders(contract_id);
CREATE INDEX idx_purchase_orders_vendor_id ON purchase_orders(vendor_id);
CREATE INDEX idx_purchase_orders_department_id ON purchase_orders(department_id);
CREATE INDEX idx_invoices_po_id ON invoices(po_id);
CREATE INDEX idx_invoices_vendor_id ON invoices(vendors_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_exceptions_invoice_id ON exceptions(invoice_id);
CREATE INDEX idx_approval_requests_status ON approval_requests(status);

-- Full-text search
CREATE INDEX idx_vendors_name_trgm ON vendors USING gin(name gin_trgm_ops);
CREATE INDEX idx_contracts_title_trgm ON contracts USING gin(title gin_trgm_ops);

-- Vector index (pgvector)
CREATE INDEX idx_documents_embedding ON documents USING hnsw(embedding vector_cosine_ops);
```

## Data Types

| Column Type | Usage |
|---|---|
| `uuid` | Primary keys, foreign keys |
| `Varchar(n)` | Short strings (names, codes, IDs) |
| `Text` | Long strings (descriptions, justifications) |
| `Decimal(15,2)` | Monetary amounts |
| `Date` | Dates (no time component) |
| `Timestamp` | Audit timestamps (with timezone) |
| `JsonB` | Flexible metadata (bank details, terms) |
| `Vector(n)` | Embeddings (pgvector) |
| `Enum` | Status fields, roles, severity levels |

## Status Values

### Contract Status
- `draft`, `active`, `expired`, `terminated`, `completed`

### Purchase Order Status
- `draft`, `submitted`, `approved`, `rejected`, `fulfilled`, `cancelled`

### Invoice Status
- `draft`, `submitted`, `approved`, `rejected`, `paid`, `overdue`, `cancelled`

### Payment Status
- `pending`, `processing`, `completed`, `failed`, `refunded`

### Exception Status
- `open`, `investigating`, `resolved`, `dismissed`

### Approval Status
- `pending`, `approved`, `rejected`, `expired`

## Constraints

- All foreign keys are `ON DELETE RESTRICT` (prevent orphaned records)
- Monetary amounts must be positive (`CHECK (amount > 0)`)
- End dates must be after start dates (`CHECK (end_date > start_date)`)
- Email addresses must be unique per user
- Invoice numbers must be unique
