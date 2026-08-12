# Event Registration API

## Overview

A serverless event registration app with a frontend form and a backend API.

## Run locally

1. Start the backend:
   ```bash
   cd Backend
   python server.py
   ```

2. Open the frontend in a browser:
   - Open [index.html](index.html) directly, or serve the project folder with a simple static server.

3. Register an event using the form.

## API routes

- GET /events
- POST /register
- GET /registrations/{email}
- DELETE /registration/{id}

## Architecture

- Frontend: HTML, CSS, JavaScript
- Backend: Python HTTP server
- AWS-ready: Lambda + API Gateway structure