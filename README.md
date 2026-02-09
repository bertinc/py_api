This tool is to serve up services and tools from a Raspberry Pi. Don't forget to use a venv when installing requirements.

API
---

Add entries (bulk)

Endpoint: POST /addentries

Accepts JSON array of entry objects, or an object with an `entries` key.

Example payload (curl):

```bash
curl -X POST http://localhost:8001/addentries \
	-H "Content-Type: application/json" \
	-d '[
		{
			"entry_date": "2026-02-07",
			"start_time": "09:00",
			"duration_minutes": 120,
			"description": "Design work",
			"notes": "Initial pass",
			"category_code": "DEV",
			"billable": 1,
			"project_code": "WASATCH_WEB_TOOL",
			"company_key": "Wasatch Photonics"
		}
	]'
```

Response:

```json
{"inserted": 1}
```
