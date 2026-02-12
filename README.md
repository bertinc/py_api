This tool is to serve up services and tools from a Raspberry Pi. Don't forget to use a venv when installing requirements.

## API Endpoints

### POST /addentry

Insert a single timesheet entry into the database.

**Request Format:**
```json
{
  "entry_date": "2026-02-12",
  "start_time": "09:00",
  "duration_minutes": 60,
  "description": "Work on project",
  "notes": "Meeting with team",
  "category_id": 1,
  "billable": 1,
  "project_id": 2,
  "company_id": 1
}
```

**Required Fields:**
- `entry_date` (YYYY-MM-DD format)
- `start_time` (HH:MM or HH:MM:SS format)
- `duration_minutes` (integer)

**Optional Fields:**
- `description` (string)
- `notes` (string)
- `category_id` (integer - the category ID)
- `billable` (0 or 1)
- `project_id` (integer - the project ID)
- `company_id` (integer - the company ID)

**Response:**
```json
{
  "inserted": 1
}
```

**C# Example:**

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class TimesheetClient
{
    private readonly string _baseUrl = "http://localhost:5000";
    private readonly HttpClient _httpClient = new HttpClient();

    public async Task AddTimesheetEntryAsync(string entryDate, string startTime, int durationMinutes, 
        string description = null, string notes = null, int? categoryId = null, int? billable = null, 
        int? projectId = null, int? companyId = null)
    {
        var entry = new
        {
            entry_date = entryDate,
            start_time = startTime,
            duration_minutes = durationMinutes,
            description = description,
            notes = notes,
            category_id = categoryId,
            billable = billable,
            project_id = projectId,
            company_id = companyId
        };

        var json = JsonSerializer.Serialize(entry);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        try
        {
            var response = await _httpClient.PostAsync($"{_baseUrl}/addentry", content);
            var responseContent = await response.Content.ReadAsStringAsync();
            
            if (response.IsSuccessStatusCode)
            {
                Console.WriteLine("Entry added successfully: " + responseContent);
            }
            else
            {
                Console.WriteLine("Error: " + responseContent);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Exception: {ex.Message}");
        }
    }
}

// Usage:
// var client = new TimesheetClient();
// await client.AddTimesheetEntryAsync("2026-02-12", "09:00", 60, "Work on project", "Meeting with team", 
//     categoryId: 1, billable: 1, projectId: 2, companyId: 1);
```

### GET /getentries

Retrieve timesheet entries between a start and end date with optional filtering.

**Query Parameters:**
- `start` (required, YYYY-MM-DD format) - start date (inclusive)
- `end` (required, YYYY-MM-DD format) - end date (inclusive)
- `period` (optional) - set to 'current_month' to get entries for the current calendar month
- `company_id` (optional, integer) - filter by company ID
- `category_id` (optional, integer) - filter by category ID
- `project_id` (optional, integer) - filter by project ID

**Example Requests:**
```
GET /getentries?start=2026-02-01&end=2026-02-28
GET /getentries?period=current_month
GET /getentries?start=2026-02-01&end=2026-02-28&company_id=1&category_id=2&project_id=3
```

**Response:**
```json
{
  "count": 5,
  "entries": [
    {
      "id": 1,
      "entry_date": "2026-02-12",
      "start_time": "09:00",
      "duration_minutes": 60,
      "end_time": "2026-02-12 10:00:00",
      "description": "Work on project",
      "notes": "Meeting with team",
      "category_id": 1,
      "category_code": "DEV",
      "category_description": "application and database development",
      "project_id": 2,
      "project_code": "GRATING_WEB_TOOL",
      "project_name": "Web Grating Design Tool",
      "company_id": 1,
      "company_name": "Wasatch Photonics",
      "billable": 1,
      "created_at": "2026-02-12 10:30:45",
      "updated_at": null
    }
  ]
}
```

**C# Example:**

```csharp
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using System.Text.Json;

public class TimesheetClient
{
    private readonly string _baseUrl = "http://localhost:5000";
    private readonly HttpClient _httpClient = new HttpClient();

    public async Task<List<Dictionary<string, object>>> GetEntriesAsync(string start, string end, 
        int? companyId = null, int? categoryId = null, int? projectId = null)
    {
        // Build query string
        var queryParams = new List<string>
        {
            $"start={Uri.EscapeDataString(start)}",
            $"end={Uri.EscapeDataString(end)}"
        };

        if (companyId.HasValue)
            queryParams.Add($"company_id={companyId}");
            
        if (categoryId.HasValue)
            queryParams.Add($"category_id={categoryId}");
            
        if (projectId.HasValue)
            queryParams.Add($"project_id={projectId}");

        var queryString = string.Join("&", queryParams);
        var url = $"{_baseUrl}/getentries?{queryString}";

        try
        {
            var response = await _httpClient.GetAsync(url);
            var responseContent = await response.Content.ReadAsStringAsync();
            
            if (response.IsSuccessStatusCode)
            {
                var jsonDoc = JsonDocument.Parse(responseContent);
                var entries = new List<Dictionary<string, object>>();
                
                if (jsonDoc.RootElement.TryGetProperty("entries", out var entriesElement))
                {
                    foreach (var entry in entriesElement.EnumerateArray())
                    {
                        var entryDict = new Dictionary<string, object>();
                        foreach (var property in entry.EnumerateObject())
                        {
                            entryDict[property.Name] = property.Value.GetRawText();
                        }
                        entries.Add(entryDict);
                    }
                }
                
                Console.WriteLine($"Retrieved {entries.Count} entries");
                return entries;
            }
            else
            {
                Console.WriteLine($"Error: {responseContent}");
                return new List<Dictionary<string, object>>();
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Exception: {ex.Message}");
            return new List<Dictionary<string, object>>();
        }
    }
}

// Usage:
// var client = new TimesheetClient();
// var entries = await client.GetEntriesAsync("2026-02-01", "2026-02-28", 
//     companyId: 1, categoryId: 2, projectId: 3);
```