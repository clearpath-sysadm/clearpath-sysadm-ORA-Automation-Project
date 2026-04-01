# ShipStation API V2 — Endpoint Reference Report

**Base URL:** `https://api.shipstation.com/v2/`
**Authentication:** All V2 calls use a single `api-key` header
**Official Docs:** https://docs.shipstation.com

---

## 1. Applying Presets

### Availability
**There is no dedicated `/v2/presets` endpoint.** Presets are a UI-only concept in ShipStation — they are saved shipping configurations (carrier, service, package type, weight, dimensions, etc.) that can only be applied through the web interface.

### API Equivalent
To replicate preset behavior via the API, pass all shipping configuration values directly in your shipment or label request body. Store your preset configurations as constants or config objects in your application and inject them into requests dynamically.

### Updating an Existing Shipment (Apply Preset Equivalent)
```
PUT https://api.shipstation.com/v2/shipments/{shipment_id}
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "carrier_id": "se-12345",
  "service_code": "ups_ground",
  "packages": [
    {
      "weight": { "value": 5, "unit": "pound" },
      "dimensions": { "unit": "inch", "length": 12, "width": 9, "height": 6 }
    }
  ]
}
```

### Notes
- There is currently no API call to reference or apply a named preset from your ShipStation account.
- If this feature is needed, contact ShipStation API support at `shippingapisupport@shipstation.com` to register the feature request.
- Monitor https://docs.shipstation.com for future additions.

---

## 2. Creating Batches

### Endpoint
```
POST https://api.shipstation.com/v2/batches
```

### Authentication
```
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `external_batch_id` | string | No | Your own unique ID for this batch |
| `batch_notes` | string | No | Label or description for the batch |
| `shipment_ids` | string[] | No* | Shipment IDs to include |
| `rate_ids` | string[] | No* | Rate IDs to include |

*At least `shipment_ids` or `rate_ids` should be provided.*

### Example Request
```bash
curl -i -X POST \
  https://api.shipstation.com/v2/batches \
  -H 'Content-Type: application/json' \
  -H 'api-key: YOUR_API_KEY_HERE' \
  -d '{
    "external_batch_id": "1daa0c22-0519-46d0-8653-9f3dc62e7d2c",
    "batch_notes": "Morning Shipments 2025-04-01",
    "shipment_ids": ["se-2102769"],
    "rate_ids": []
  }'
```

### Example Response
```json
{
  "batch_id": "se-1013790",
  "external_batch_id": "1daa0c22-0519-46d0-8653-9f3dc62e7d2c",
  "batch_notes": "Morning Shipments 2025-04-01",
  "created_at": "2025-04-01T15:24:46.657Z",
  "errors": 0,
  "warnings": 0,
  "completed": 0,
  "count": 1,
  "batch_shipments_url": {
    "href": "https://api.shipstation.com/v2/shipments?batch_id=se-1013790"
  },
  "batch_labels_url": {
    "href": "https://api.shipstation.com/v2/labels?batch_id=se-1013790"
  },
  "batch_errors_url": {
    "href": "https://api.shipstation.com/v2/batches/se-1013790/errors"
  },
  "label_download": {
    "href": "https://api.shipstation.com/v2/downloads/1/uths7PctKUqbM4OfmgzXLg/label-1013790.pdf"
  },
  "status": "open"
}
```

### All Batch Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v2/batches` | List all batches |
| `POST` | `/v2/batches` | Create a batch |
| `GET` | `/v2/batches/{batch_id}` | Get batch details |
| `PUT` | `/v2/batches/{batch_id}` | Update a batch |
| `DELETE` | `/v2/batches/{batch_id}` | Delete a batch |
| `POST` | `/v2/batches/{batch_id}/add` | Add shipments to a batch |
| `POST` | `/v2/batches/{batch_id}/remove` | Remove shipments from a batch |
| `POST` | `/v2/batches/{batch_id}/process/labels` | Process and purchase all labels in a batch |
| `GET` | `/v2/batches/{batch_id}/errors` | Get batch errors |
| `GET` | `/v2/batches/external_batch_id/{id}` | Look up batch by external ID |

---

## 3. Adding Orders/Shipments to a Batch

### Key Requirement
All shipments added to a batch **must use a `warehouse_id`** instead of a `ship_from` address block. All shipments in the same batch must share the **same `warehouse_id`**.

### Method 1 — POST to /add (Recommended)

```
POST https://api.shipstation.com/v2/batches/{batch_id}/add
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "shipment_ids": ["se-2102769", "se-2102770"],
  "rate_ids": []
}
```

**Response:** `HTTP 204 No Content` on success.

```bash
curl -i -X POST \
  https://api.shipstation.com/v2/batches/se-1013790/add \
  -H 'api-key: YOUR_API_KEY_HERE' \
  -H 'Content-Type: application/json' \
  -d '{
    "shipment_ids": ["se-2102769"],
    "rate_ids": []
  }'
```

### Method 2 — PUT to update the batch

```
PUT https://api.shipstation.com/v2/batches/{batch_id}
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "shipment_ids": ["se-2102769"],
  "rate_ids": []
}
```

**Response:** `HTTP 204 No Content` on success.

### Removing from a Batch

```
POST https://api.shipstation.com/v2/batches/{batch_id}/remove
```

```json
{
  "shipment_ids": ["se-2102769"],
  "rate_ids": []
}
```

**Response:** `HTTP 204 No Content` on success.

---

## 4. Adding Packages to Shipments

### Overview
V2 fully supports multi-package shipments. Packages are defined as an array within the shipment body — each package can have its own weight, dimensions, and package type.

### Creating a Shipment with Packages

```
POST https://api.shipstation.com/v2/shipments
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "carrier_id": "se-12345",
  "service_code": "usps_priority_mail",
  "warehouse_id": "se-654321",
  "ship_to": {
    "name": "Customer Name",
    "address_line1": "456 Elm St",
    "city_locality": "New York",
    "state_province": "NY",
    "postal_code": "10001",
    "country_code": "US"
  },
  "packages": [
    {
      "package_code": "small_flat_rate_box",
      "weight": {
        "value": 2.5,
        "unit": "pound"
      },
      "dimensions": {
        "unit": "inch",
        "length": 10,
        "width": 8,
        "height": 4
      }
    },
    {
      "package_code": "medium_flat_rate_box",
      "weight": {
        "value": 5.0,
        "unit": "pound"
      },
      "dimensions": {
        "unit": "inch",
        "length": 14,
        "width": 12,
        "height": 3.5
      }
    }
  ]
}
```

### Package Object Fields

| Field | Type | Description |
|---|---|---|
| `package_code` | string | Carrier package type (e.g. `small_flat_rate_box`, `package`) |
| `weight.value` | number | Weight amount |
| `weight.unit` | string | `pound`, `ounce`, `gram`, `kilogram` |
| `dimensions.unit` | string | `inch` or `centimeter` |
| `dimensions.length` | number | Length |
| `dimensions.width` | number | Width |
| `dimensions.height` | number | Height |

### Updating Packages on an Existing Shipment

```
PUT https://api.shipstation.com/v2/shipments/{shipment_id}
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "packages": [
    {
      "package_code": "package",
      "weight": { "value": 3, "unit": "pound" },
      "dimensions": { "unit": "inch", "length": 12, "width": 9, "height": 6 }
    }
  ]
}
```

### Custom Package Types
You can create reusable custom package types (instead of using carrier defaults) via:

```
POST https://api.shipstation.com/v2/packages
GET  https://api.shipstation.com/v2/packages
PUT  https://api.shipstation.com/v2/packages/{package_id}
DELETE https://api.shipstation.com/v2/packages/{package_id}
```

---

## 5. Printing Labels

### Single Label — Purchase Immediately

```
POST https://api.shipstation.com/v2/labels
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "shipment": {
    "carrier_id": "se-12345",
    "service_code": "usps_priority_mail",
    "ship_from": {
      "name": "Your Name",
      "company_name": "Your Company",
      "address_line1": "123 Main St",
      "city_locality": "Austin",
      "state_province": "TX",
      "postal_code": "78701",
      "country_code": "US",
      "phone": "512-555-0100"
    },
    "ship_to": {
      "name": "Customer Name",
      "address_line1": "456 Elm St",
      "city_locality": "New York",
      "state_province": "NY",
      "postal_code": "10001",
      "country_code": "US"
    },
    "packages": [
      {
        "package_code": "small_flat_rate_box",
        "weight": { "value": 2.5, "unit": "pound" }
      }
    ]
  },
  "label_layout": "4x6",
  "label_format": "pdf",
  "test_label": false
}
```

### Label Format Options

| Field | Options | Notes |
|---|---|---|
| `label_format` | `pdf`, `png`, `zpl` | PDF recommended — supported by all carriers |
| `label_layout` | `4x6`, `letter` | Letter only supported for PDF format |
| `test_label` | `true` / `false` | Set `true` to generate a non-billable test label |

### Bulk Labels — Process a Batch

```
POST https://api.shipstation.com/v2/batches/{batch_id}/process/labels
api-key: YOUR_API_KEY_HERE
Content-Type: application/json
```

```json
{
  "ship_date": "2025-04-01T05:00:00.000Z",
  "label_layout": "4x6",
  "label_format": "pdf"
}
```

After processing, retrieve the label download URL from the batch details:

```
GET https://api.shipstation.com/v2/batches/{batch_id}
```

The response includes a `label_download.href` you can use to download the combined PDF.

### Other Label Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v2/labels` | Purchase a single label |
| `GET` | `/v2/labels/{label_id}` | Get label details and download link |
| `PUT` | `/v2/labels/{label_id}/void` | Void a label |
| `POST` | `/v2/labels/return` | Create a return label |
| `GET` | `/v2/labels?batch_id={batch_id}` | List all labels in a batch |

---

## End-to-End Workflow Summary

```
1. Create shipments       POST /v2/shipments          (with packages array)
2. Create a batch         POST /v2/batches
3. Add shipments          POST /v2/batches/{id}/add
4. Process labels         POST /v2/batches/{id}/process/labels
5. Download labels        GET  /v2/batches/{id}        (use label_download.href)
6. Void if needed         PUT  /v2/labels/{label_id}/void
```

---

## What Is NOT Available in V2

| Feature | Status |
|---|---|
| Applying named presets | Not available — UI only |
| Lot-level inventory read (GET) | Not available — POST accepts lot, GET does not return it |
| Order management / import | Not in V2 — use V1 (`ssapi.shipstation.com`) |
| V1 Basic Auth | Not supported in V2 — V2 uses `api-key` header only |

---

*Report generated: April 1, 2026*
*Source: https://docs.shipstation.com*
