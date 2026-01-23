# IFC File Splitter

A tool for filtering and splitting IFC (Industry Foundation Classes) files. 
It allows you to extract specific elements from an IFC model based on **GUIDs** or **IfcTypes** (e.g., IfcBeam, IfcWall) while maintaining the necessary spatial structure.

This project offers two interfaces:
1.  **CLI (Command Line Interface)** for direct file processing.
2.  **REST API** for building services or integrating into web apps with job persistence (survives server restarts).

---

## CLI Usage

The entry point is `main.py`. You can see all commands with `--help`.

### 1. Split an IFC File
Filter an IFC file to keep only specific elements.

**By GUIDs:**
```bash
python main.py split "input.ifc" "output_filtered.ifc" --guid "3aBdFe1234567890abcdef" --guid "1xYz9876543210fedcba"
```

**By IfcTypes:**
```bash
python main.py split "input.ifc" "beams.ifc" --type "IfcBeam" --type "IfcColumn"
```

**Combined:**
```bash
python main.py split "full_model.ifc" "subset.ifc" -t "IfcWall" -g "3aBdFe..." 
```

### 2. Run the REST API Server
Start the dedicated API server for handling requests asynchronously.

```bash
# Start server on default port 8000
python main.py serve

# Custom host/port with auto-reload
python main.py serve --host 0.0.0.0 --port 8080 --reload
```

---

## REST API Usage

The API is built with FastAPI. Once the server is running (default: `http://localhost:8000`), you can access the interactive documentation at:
-   **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
-   **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Health Check

Check if the API is running and see job persistence status:

```bash
curl http://localhost:8000/api/v1/health
```

```bash
http GET http://localhost:8000/api/v1/health
```

Returns information about data directories and active jobs.

### Workflow Example using `curl`

#### 1. Submit a Job
Upload a file and specify filters. The processing happens in the background.

```bash
# Keep only IfcBeam elements
curl -X "POST" \
  "http://localhost:8000/api/v1/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./my_building.ifc" \
  -F "ifc_types=IfcBeam,IfcColumn" \
  -F "guids="
```

**With Webhook Callback:**
```bash
# Get notified when job completes
curl -X "POST" \
  "http://localhost:8000/api/v1/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./my_building.ifc" \
  -F "ifc_types=IfcWall" \
  -F "callback_url=https://your-domain.com/webhook/ifc-complete"
```

The callback URL will receive a POST request when the job completes:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
  "status": "completed",
  "error": null,
  "output_file": "/path/to/output.ifc",
  "created_at": "2026-01-22T18:00:00"
}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
  "status": "pending",
  "message": "File uploaded and processing started."
}
```

#### 2. Check Job Status
Use the `job_id` from the previous step.

```bash
curl -X "GET" "http://localhost:8000/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-56789abcdef0"
```

**Response (Processing):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
  "status": "processing",
  "message": "Processing..."
}
```

**Response (Completed):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
  "status": "completed",
  "message": "Completed",
  "output_file": "D:\\path\\to\\data\\processed\\..._filtered.ifc"
}
```

#### 3. Download Result
Once the status is `completed`.

```bash
curl -X "GET" \
  "http://localhost:8000/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-56789abcdef0/download" \
  --output my_filtered_result.ifc
```

### Workflow Example using `httpie`

#### 1. Submit a Job
Upload a file and specify filters.

```bash
# Keep only IfcBeam elements
http -f POST http://localhost:8000/api/v1/process \
    file@./my_building.ifc \
    ifc_types=IfcBeam,IfcColumn \
    guids=
```

```powershell
http -f POST http://localhost:8000/api/v1/process file@./testVoid.ifc ifc_types=IfcPanel
http -f POST https://razor-ifc.onrender.com/api/v1/process file@./Raster.ifc ifc_types="IfcWall"
```

```powershell
http -f POST http://localhost:8000/api/v1/process `
    file@./testVoid.ifc `
    ifc_types=IfcPanel
```


#### 2. Check Job Status

```bash
http GET http://localhost:8000/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-56789abcdef0
```

#### 3. Download Result

```bash
http --download GET http://localhost:8000/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-56789abcdef0/download \
    -o my_filtered_result.ifc
```

---
