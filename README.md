# Microservices Starter Architecture

This repository contains a starter skeleton for a 3-service architecture:

\\\
+---------------------+        validates tokens        +-----------------+
¦   FastAPI Gateway   ¦ -----------------------------? ¦   Auth Service  ¦
¦   (Service 1)       ¦                                ¦   (Service 2)   ¦
¦                     ¦        forwards payload        +-----------------+
¦                     ¦ -----------------------------? +---------------------+
+---------------------+                                ¦ Data Processing     ¦
                                                       ¦ Engine (Service 3)  ¦
                                                       +---------------------+
\\\

## Services

| Service | Path | Port | Responsibility |
|---|---|---|---|
| FastAPI Gateway | \gateway/\ | 8000 | Public entrypoint. Validates incoming JWT tokens against the Auth Service, then forwards request payloads to the Data Processing Engine. |
| Auth Service | \uth_service/\ | 8001 | Issues and validates JWT tokens, manages user accounts. |
| Data Processing Engine | \data_processing_engine/\ | 8002 | Performs the actual business/data processing logic on payloads forwarded by the Gateway. |

## Running locally

\\\ash
cp .env.example .env
docker-compose up --build
\\\

The Gateway will be available at \http://localhost:8000\.
