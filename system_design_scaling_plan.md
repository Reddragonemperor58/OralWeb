# System Design & Scaling Plan: OralDiag SaaS

Deploying a web application from a local environment to a production environment that handles 1,000s of real-time users requires shifting from "it runs" to "it scales."

Since your goal is to support many concurrent users while keeping **AWS costs as low as possible**, we need to redesign your architecture to be horizontally scalable and serverless wherever feasible.

---

## 1. What Your Codebase is Currently Lacking

Before deploying, your codebase has a few bottlenecks that will crash or slow down the app under heavy load:

> [!WARNING]
> **Synchronous ML Blocking**
> In `backend/analysis.py`, your TensorFlow model prediction (`model.predict()`) runs synchronously. Because FastAPI is asynchronous, this heavy CPU computation will block the entire event loop. If one user uploads an image, other users won't be able to log in until the prediction finishes.

> [!WARNING]
> **The SQLite Database**
> You are using `clinic.db` (SQLite). SQLite locks the whole database on every write. With thousands of users, concurrent database writes (e.g., saving patients) will fail with "Database is locked" errors. 

> [!WARNING]
> **Heavy ML Memory Footprint**
> `tf.keras.models.load_model()` loads your 200MB model into RAM. If you run 4 API workers to handle traffic, that's 800MB just for the model. 

> [!IMPORTANT]
> **Streamlit Stateful Connections**
> Streamlit uses continuous WebSocket connections to maintain state. It doesn't scale like a normal website. If you spin up multiple Streamlit servers, a user's request might hit a different server where their state doesn't exist, breaking the app.

---

## 2. The Production Architecture on AWS

To scale effectively but cheaply, we will use a **Containerized Serverless Architecture** using AWS Fargate and managed services.

### Level 1: Frontend (Streamlit)
*   **Action:** Dockerize your `frontend` directory.
*   **AWS Service:** Deploy to **AWS ECS (Elastic Container Service) on Fargate**. Fargate is serverless compute for containers. You only pay when it's running.
*   **Scaling Fix:** Put an **Application Load Balancer (ALB)** in front of it and **Enable Sticky Sessions**. This ensures a user's WebSocket connection always routes to the same Streamlit container.

### Level 2: Backend (FastAPI)
*   **Action:** Dockerize your `backend`. Update `main.py` to use `gunicorn` with `uvicorn` workers for production routing.
*   **AWS Service:** Deploy to a separate **AWS ECS Fargate** service.
*   **Scaling Fix:** Configure ECS Auto-scaling. Tell AWS: *"If CPU usage hits 70%, add another container."* Fargate will scale from 1 API to 10 APIs automatically based on traffic.

### Level 3: Database & Storage
*   **Database:** Migrate from SQLite to **Amazon RDS for PostgreSQL**. A single `db.t4g.micro` instance is very cheap (~$12/month) and handles thousands of concurrent reads/writes perfectly. Update `database.py` to use the AWS Postgres URL.
*   **Image Storage:** Do NOT store user uploaded images in the FastAPI container or database. Use **Amazon S3**.
    *   *Workflow:* Frontend asks FastAPI for a "Presigned S3 URL". The frontend uploads the heavy image directly to S3. FastAPI only saves the S3 Link to the database. This drastically reduces the load on your API.

### Level 4: The ML Model (The cost-saving trick)
Deploying ML models is the most expensive part of cloud hosting.

*   **Option A: SageMaker Serverless Inference (Recommended for Cost)**
    Instead of loading the TF model in FastAPI, deploy the `.h5` model to AWS SageMaker Serverless.
    *   *Why?* You only pay per inference (when a doctor clicks analyze). If the app is idle at 3 AM, your ML cost is $0.
    *   *Code Change:* Your `backend/analysis.py` will remove TensorFlow completely, and instead use the `boto3` library to send the image to SageMaker and get the result.
*   **Option B: Background task Queue (Alternative)**
    If you must keep the model in FastAPI, route predictions through an asynchronous task queue like **Celery + Redis**. This ensures the main web server isn't blocked by the heavy math.

---

## 3. Step-by-Step Implementation Map

To move forward with this, here is the order of operations you should tackle:

1.  **Switch the Database locally:** Install Postgres locally, change the connection string in `database.py`, and test locally.
2.  **Add S3:** Create an AWS Account, generate an IAM Key, and update your code to upload patient pictures to S3 using the `boto3` Python library.
3.  **Dockerize Everything:** Create a `Dockerfile` for the frontend and a `Dockerfile` for the backend. Use `docker-compose` to test them talking to each other locally.
4.  **Offload the Model:** Remove `keras` from `analysis.py`. Run your `/analyze/dl` function inside a Python Thread (`asyncio.to_thread`) OR move it to an external serverless function.
5.  **Deploy to AWS:** Setup an ALB, ECS clusters, and RDS.

## Summary of Tech Changes Needed:
```diff
# requirements.txt improvements
- tensorflow==2.15.0  (Extract to a separate microservice/Sagemaker)
+ psycopg2-binary     (For PostgreSQL connection)
+ gunicorn            (Production ASGI server)
+ boto3               (AWS SDK for Python - S3 integration)
```
