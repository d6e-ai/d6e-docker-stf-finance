# D6E Docker STF Development - Examples

Real-world implementation examples for common use cases.

## Example 1: Data Validation STF

Validates incoming data against configurable rules.

**Use Case:** Validate customer data before inserting into database.

**Input:**
```json
{
  "input": {
    "operation": "validate",
    "data": [
      {"name": "John Doe", "email": "john@example.com", "age": 30},
      {"name": "Jane", "email": "invalid-email", "age": -5}
    ],
    "rules": {
      "name": {"required": true, "min_length": 2},
      "email": {"required": true, "pattern": "^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"},
      "age": {"required": true, "min": 0, "max": 150}
    }
  }
}
```

**Implementation:**
```python
import re

def validate_field(value, rules):
    """Validate a single field against rules"""
    errors = []
    
    if rules.get("required") and not value:
        errors.append("Field is required")
        return errors
    
    if "min_length" in rules and len(str(value)) < rules["min_length"]:
        errors.append(f"Must be at least {rules['min_length']} characters")
    
    if "max_length" in rules and len(str(value)) > rules["max_length"]:
        errors.append(f"Must be at most {rules['max_length']} characters")
    
    if "pattern" in rules and not re.match(rules["pattern"], str(value)):
        errors.append("Invalid format")
    
    if "min" in rules and float(value) < rules["min"]:
        errors.append(f"Must be at least {rules['min']}")
    
    if "max" in rules and float(value) > rules["max"]:
        errors.append(f"Must be at most {rules['max']}")
    
    return errors

def process(user_input, sources, context):
    data = user_input.get("data", [])
    rules = user_input.get("rules", {})
    
    validation_results = []
    valid_count = 0
    invalid_count = 0
    
    for i, item in enumerate(data):
        item_errors = {}
        
        for field, field_rules in rules.items():
            value = item.get(field)
            field_errors = validate_field(value, field_rules)
            
            if field_errors:
                item_errors[field] = field_errors
        
        if item_errors:
            validation_results.append({
                "row": i,
                "data": item,
                "errors": item_errors,
                "valid": False
            })
            invalid_count += 1
        else:
            validation_results.append({
                "row": i,
                "data": item,
                "valid": True
            })
            valid_count += 1
    
    return {
        "status": "success",
        "total": len(data),
        "valid": valid_count,
        "invalid": invalid_count,
        "results": validation_results
    }
```

**Output:**
```json
{
  "output": {
    "status": "success",
    "total": 2,
    "valid": 1,
    "invalid": 1,
    "results": [
      {
        "row": 0,
        "data": {"name": "John Doe", "email": "john@example.com", "age": 30},
        "valid": true
      },
      {
        "row": 1,
        "data": {"name": "Jane", "email": "invalid-email", "age": -5},
        "errors": {
          "email": ["Invalid format"],
          "age": ["Must be at least 0"]
        },
        "valid": false
      }
    ]
  }
}
```

## Example 2: External API Integration

Fetches data from external API and stores in D6E database.

**Use Case:** Fetch weather data from external API and store for reporting.

**Input:**
```json
{
  "input": {
    "operation": "fetch_weather",
    "location": "Tokyo",
    "api_key": "your_api_key"
  }
}
```

**Implementation:**
```python
import requests
from datetime import datetime

def fetch_weather_data(location, api_key):
    """Fetch weather from external API"""
    url = "https://api.weatherapi.com/v1/current.json"
    params = {
        "key": api_key,
        "q": location
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Weather API error: {str(e)}")

def process(user_input, sources, api_client):
    location = user_input.get("location")
    api_key = user_input.get("api_key")
    
    if not location or not api_key:
        raise ValueError("Missing required fields: location, api_key")
    
    # Fetch weather data
    weather_data = fetch_weather_data(location, api_key)
    
    # Extract relevant information
    current = weather_data.get("current", {})
    location_data = weather_data.get("location", {})
    
    # Store in database
    sql = f"""
        INSERT INTO weather_data (
            location,
            temperature,
            humidity,
            condition,
            wind_speed,
            recorded_at
        ) VALUES (
            '{location_data.get("name")}',
            {current.get("temp_c")},
            {current.get("humidity")},
            '{current.get("condition", {}).get("text")}',
            {current.get("wind_kph")},
            '{datetime.utcnow().isoformat()}'
        )
    """
    
    api_client.execute_sql(sql)
    
    return {
        "status": "success",
        "location": location_data.get("name"),
        "temperature": current.get("temp_c"),
        "humidity": current.get("humidity"),
        "condition": current.get("condition", {}).get("text"),
        "stored": True
    }
```

**Output:**
```json
{
  "output": {
    "status": "success",
    "location": "Tokyo",
    "temperature": 22.5,
    "humidity": 65,
    "condition": "Partly cloudy",
    "stored": true
  }
}
```

## Example 3: Data Aggregation and Reporting

Aggregates data from multiple tables and generates a report.

**Use Case:** Generate monthly sales report with customer segmentation.

**Input:**
```json
{
  "input": {
    "operation": "generate_report",
    "report_type": "monthly_sales",
    "month": "2024-01",
    "include_segments": true
  }
}
```

**Implementation:**
```python
def generate_sales_report(api_client, month):
    """Generate comprehensive sales report"""
    # Get total sales
    total_sql = f"""
        SELECT 
            COUNT(*) as order_count,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM orders
        WHERE DATE_TRUNC('month', created_at) = '{month}-01'
    """
    totals = api_client.execute_sql(total_sql)
    
    # Get sales by product category
    category_sql = f"""
        SELECT 
            p.category,
            COUNT(oi.id) as item_count,
            SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE_TRUNC('month', o.created_at) = '{month}-01'
        GROUP BY p.category
        ORDER BY revenue DESC
    """
    categories = api_client.execute_sql(category_sql)
    
    # Get customer segments
    segments_sql = f"""
        SELECT 
            CASE 
                WHEN total_spent > 1000 THEN 'premium'
                WHEN total_spent > 500 THEN 'regular'
                ELSE 'basic'
            END as segment,
            COUNT(*) as customer_count,
            SUM(total_spent) as segment_revenue
        FROM (
            SELECT 
                customer_id,
                SUM(total_amount) as total_spent
            FROM orders
            WHERE DATE_TRUNC('month', created_at) = '{month}-01'
            GROUP BY customer_id
        ) customer_totals
        GROUP BY segment
        ORDER BY segment_revenue DESC
    """
    segments = api_client.execute_sql(segments_sql)
    
    # Get top customers
    top_customers_sql = f"""
        SELECT 
            c.name,
            c.email,
            COUNT(o.id) as order_count,
            SUM(o.total_amount) as total_spent
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE DATE_TRUNC('month', o.created_at) = '{month}-01'
        GROUP BY c.id, c.name, c.email
        ORDER BY total_spent DESC
        LIMIT 10
    """
    top_customers = api_client.execute_sql(top_customers_sql)
    
    return {
        "status": "success",
        "month": month,
        "summary": totals["rows"][0],
        "by_category": categories["rows"],
        "by_segment": segments["rows"],
        "top_customers": top_customers["rows"]
    }

def process(user_input, sources, api_client):
    report_type = user_input.get("report_type")
    month = user_input.get("month")
    
    if report_type == "monthly_sales":
        return generate_sales_report(api_client, month)
    else:
        raise ValueError(f"Unknown report type: {report_type}")
```

**Output:**
```json
{
  "output": {
    "status": "success",
    "month": "2024-01",
    "summary": {
      "order_count": 1523,
      "total_revenue": 245830.50,
      "avg_order_value": 161.42
    },
    "by_category": [
      {"category": "Electronics", "item_count": 856, "revenue": 125430.00},
      {"category": "Clothing", "item_count": 1240, "revenue": 85200.50},
      {"category": "Books", "item_count": 432, "revenue": 35200.00}
    ],
    "by_segment": [
      {"segment": "premium", "customer_count": 45, "revenue": 98500.00},
      {"segment": "regular", "customer_count": 234, "revenue": 115330.50},
      {"segment": "basic", "customer_count": 890, "revenue": 32000.00}
    ],
    "top_customers": [
      {"name": "Company A", "email": "contact@companya.com", "order_count": 25, "total_spent": 12500.00}
    ]
  }
}
```

## Example 4: Batch Data Processing

Processes large datasets in batches with progress tracking.

**Use Case:** Process and enrich customer records in batches.

**Input:**
```json
{
  "input": {
    "operation": "enrich_customers",
    "batch_size": 100,
    "enrichment_type": "add_location_data"
  }
}
```

**Implementation:**
```python
def enrich_customer_batch(api_client, customers, enrichment_type):
    """Enrich a batch of customers"""
    enriched = []
    
    for customer in customers:
        if enrichment_type == "add_location_data":
            # Fetch location data (simplified)
            location_sql = f"""
                SELECT city, state, country, timezone
                FROM locations
                WHERE postal_code = '{customer.get("postal_code")}'
                LIMIT 1
            """
            location_result = api_client.execute_sql(location_sql)
            
            if location_result["rows"]:
                location = location_result["rows"][0]
                
                # Update customer record
                update_sql = f"""
                    UPDATE customers
                    SET 
                        city = '{location["city"]}',
                        state = '{location["state"]}',
                        country = '{location["country"]}',
                        timezone = '{location["timezone"]}',
                        updated_at = NOW()
                    WHERE id = '{customer["id"]}'
                """
                api_client.execute_sql(update_sql)
                enriched.append(customer["id"])
    
    return enriched

def process(user_input, sources, api_client):
    batch_size = user_input.get("batch_size", 100)
    enrichment_type = user_input.get("enrichment_type")
    
    # Get total count
    count_sql = "SELECT COUNT(*) as total FROM customers WHERE city IS NULL"
    count_result = api_client.execute_sql(count_sql)
    total = count_result["rows"][0]["total"]
    
    # Process in batches
    offset = 0
    processed = 0
    batches = 0
    
    while offset < total:
        # Fetch batch
        batch_sql = f"""
            SELECT id, postal_code
            FROM customers
            WHERE city IS NULL
            LIMIT {batch_size}
            OFFSET {offset}
        """
        batch_result = api_client.execute_sql(batch_sql)
        customers = batch_result["rows"]
        
        if not customers:
            break
        
        # Enrich batch
        enriched = enrich_customer_batch(api_client, customers, enrichment_type)
        
        processed += len(enriched)
        batches += 1
        offset += batch_size
        
        # Log progress
        progress = (processed / total) * 100
        logging.info(f"Progress: {progress:.1f}% ({processed}/{total})")
    
    return {
        "status": "success",
        "total": total,
        "processed": processed,
        "batches": batches,
        "enrichment_type": enrichment_type
    }
```

## Example 5: Multi-Step Workflow with Sources

Uses output from previous workflow steps.

**Use Case:** Fetch data, validate, then insert into database.

**Workflow Steps:**
1. `data_fetcher`: Fetches raw data from external API
2. `data_validator`: Validates the fetched data (this example)
3. `data_inserter`: Inserts valid data into database

**Input (Step 2 - Validator):**
```json
{
  "input": {
    "operation": "validate_and_filter"
  },
  "sources": {
    "data_fetcher": {
      "output": {
        "status": "success",
        "records": [
          {"id": 1, "name": "Product A", "price": 99.99, "stock": 50},
          {"id": 2, "name": "Product B", "price": -10.00, "stock": 0},
          {"id": 3, "name": "", "price": 149.99, "stock": 25}
        ]
      }
    }
  }
}
```

**Implementation:**
```python
def validate_record(record):
    """Validate a single record"""
    errors = []
    
    if not record.get("name"):
        errors.append("Name is required")
    
    if record.get("price", 0) <= 0:
        errors.append("Price must be positive")
    
    if record.get("stock", 0) < 0:
        errors.append("Stock cannot be negative")
    
    return errors

def process(user_input, sources, context):
    # Get data from previous step
    fetcher_output = sources.get("data_fetcher", {}).get("output", {})
    records = fetcher_output.get("records", [])
    
    if not records:
        raise ValueError("No records from data_fetcher step")
    
    valid_records = []
    invalid_records = []
    
    for record in records:
        errors = validate_record(record)
        
        if errors:
            invalid_records.append({
                "record": record,
                "errors": errors
            })
        else:
            valid_records.append(record)
    
    return {
        "status": "success",
        "total": len(records),
        "valid": valid_records,
        "invalid": invalid_records,
        "valid_count": len(valid_records),
        "invalid_count": len(invalid_records)
    }
```

**Output:**
```json
{
  "output": {
    "status": "success",
    "total": 3,
    "valid": [
      {"id": 1, "name": "Product A", "price": 99.99, "stock": 50}
    ],
    "invalid": [
      {
        "record": {"id": 2, "name": "Product B", "price": -10.00, "stock": 0},
        "errors": ["Price must be positive"]
      },
      {
        "record": {"id": 3, "name": "", "price": 149.99, "stock": 25},
        "errors": ["Name is required"]
      }
    ],
    "valid_count": 1,
    "invalid_count": 2
  }
}
```

## Example 6: Scheduled Report Generator

Generates and emails reports on a schedule.

**Use Case:** Daily sales summary sent via email.

**Input:**
```json
{
  "input": {
    "operation": "daily_summary",
    "date": "2024-01-15",
    "email_to": "management@company.com"
  }
}
```

**Implementation:**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def generate_daily_summary(api_client, date):
    """Generate daily sales summary"""
    sql = f"""
        SELECT 
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(*) as total_orders,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value,
            MAX(total_amount) as highest_order
        FROM orders
        WHERE DATE(created_at) = '{date}'
    """
    result = api_client.execute_sql(sql)
    return result["rows"][0]

def send_email(to_address, subject, body):
    """Send email via SMTP"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_address
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'html'))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

def format_report_html(summary, date):
    """Format summary as HTML"""
    return f"""
    <html>
    <body>
        <h2>Daily Sales Summary - {date}</h2>
        <table border="1">
            <tr><td>Unique Customers</td><td>{summary['unique_customers']}</td></tr>
            <tr><td>Total Orders</td><td>{summary['total_orders']}</td></tr>
            <tr><td>Total Revenue</td><td>${summary['total_revenue']:.2f}</td></tr>
            <tr><td>Average Order Value</td><td>${summary['avg_order_value']:.2f}</td></tr>
            <tr><td>Highest Order</td><td>${summary['highest_order']:.2f}</td></tr>
        </table>
    </body>
    </html>
    """

def process(user_input, sources, api_client):
    date = user_input.get("date", datetime.now().strftime("%Y-%m-%d"))
    email_to = user_input.get("email_to")
    
    # Generate summary
    summary = generate_daily_summary(api_client, date)
    
    # Format and send email
    html_body = format_report_html(summary, date)
    send_email(
        to_address=email_to,
        subject=f"Daily Sales Summary - {date}",
        body=html_body
    )
    
    return {
        "status": "success",
        "date": date,
        "summary": summary,
        "email_sent": True,
        "email_to": email_to
    }
```

## Example 7: Real-time Data Sync

Syncs data from external system to D6E database.

**Use Case:** Sync inventory updates from warehouse system.

**Input:**
```json
{
  "input": {
    "operation": "sync_inventory",
    "warehouse_api_url": "https://warehouse.example.com/api",
    "api_key": "warehouse_key"
  }
}
```

**Implementation:**
```python
def fetch_inventory_updates(warehouse_url, api_key, since_timestamp):
    """Fetch inventory updates since last sync"""
    response = requests.get(
        f"{warehouse_url}/inventory/updates",
        params={"since": since_timestamp},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def sync_inventory_item(api_client, item):
    """Sync single inventory item"""
    # Check if product exists
    check_sql = f"SELECT id FROM products WHERE sku = '{item['sku']}'"
    result = api_client.execute_sql(check_sql)
    
    if result["rows"]:
        # Update existing
        update_sql = f"""
            UPDATE products
            SET 
                stock_quantity = {item['quantity']},
                last_sync_at = NOW()
            WHERE sku = '{item['sku']}'
        """
        api_client.execute_sql(update_sql)
        return "updated"
    else:
        # Insert new
        insert_sql = f"""
            INSERT INTO products (sku, name, stock_quantity, last_sync_at)
            VALUES ('{item['sku']}', '{item['name']}', {item['quantity']}, NOW())
        """
        api_client.execute_sql(insert_sql)
        return "inserted"

def process(user_input, sources, api_client):
    warehouse_url = user_input.get("warehouse_api_url")
    api_key = user_input.get("api_key")
    
    # Get last sync timestamp
    last_sync_sql = "SELECT MAX(last_sync_at) as last_sync FROM products"
    last_sync_result = api_client.execute_sql(last_sync_sql)
    last_sync = last_sync_result["rows"][0].get("last_sync") or "1970-01-01T00:00:00Z"
    
    # Fetch updates
    updates = fetch_inventory_updates(warehouse_url, api_key, last_sync)
    
    # Sync each item
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    
    for item in updates:
        try:
            action = sync_inventory_item(api_client, item)
            stats[action] += 1
        except Exception as e:
            logging.error(f"Failed to sync {item['sku']}: {str(e)}")
            stats["errors"] += 1
    
    return {
        "status": "success",
        "synced_at": datetime.utcnow().isoformat(),
        "total_updates": len(updates),
        "stats": stats
    }
```

## Testing Your Docker STF

### Local Test Script

**test-local.sh:**
```bash
#!/bin/bash

set -e

IMAGE_NAME="${1:-my-stf:latest}"

# Test 1: Basic operation
echo "Test 1: Basic operation"
echo '{
  "workspace_id": "test-workspace",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "test"
  },
  "sources": {}
}' | docker run --rm -i $IMAGE_NAME

# Test 2: With data
echo "Test 2: With data"
echo '{
  "workspace_id": "test-workspace",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "validate",
    "data": [
      {"name": "Test", "email": "test@example.com"}
    ]
  },
  "sources": {}
}' | docker run --rm -i $IMAGE_NAME

echo "✅ All tests passed!"
```

Make executable and run:
```bash
chmod +x test-local.sh
./test-local.sh my-stf:latest
```
