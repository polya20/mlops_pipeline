

# Production-Grade Jackpot Optimizer MLOps Pipeline

This repository contains the source code and infrastructure for a fully automated, serverless MLOps pipeline on AWS. The goal of this project is to provide weekly, data-driven jackpot recommendations for the Postcode Lottery, moving beyond an exploratory notebook to a production-ready system that is reproducible, scalable, and secure.

The core of the project is to productionize a sales prediction model and wrap it in a robust optimization engine that respects real-world business and regulatory constraints.

## Table of Contents

1.  [Architecture Overview](#1-architecture-overview)
2.  [Key MLOps Features](#2-key-mlops-features)
3.  [End-to-End Workflow](#3-end-to-end-workflow)
4.  [Project Structure](#4-project-structure)
5.  [Local Development Setup](#5-local-development-setup)
6.  [Onboarding a New Country](#6-onboarding-a-new-country)
7.  [Technology Stack & Justification](#7-technology-stack--justification)

---

### **1. Architecture Overview**

The pipeline is event-driven, serverless, and orchestrated by **AWS Step Functions**. It is deployed and managed entirely via a CI/CD pipeline using **GitHub Actions** and the **AWS CDK (Cloud Development Kit)**.

![Architecture Diagram](https-your-diagram-image-url.png) <!-- It's highly recommended to create and link to an architecture diagram -->

The architecture consists of two main loops:
*   **CI/CD & Deployment Flow:** Triggered by `git push` to the `main` branch. This loop automatically tests, builds, and deploys the entire infrastructure, ensuring a safe and repeatable deployment process.
*   **Weekly MLOps Execution Flow:** Triggered by a weekly **Amazon EventBridge** cron job. This is the core production pipeline that runs the workflow for each country to generate and deliver the final recommendations.

---

### **2. Key MLOps Features**

This pipeline was designed with senior-level MLOps principles as a first-class priority:

*   **Serverless-First Design:** Leverages AWS Lambda, Step Functions, and managed SageMaker jobs to minimize operational overhead and cost. There are no idle servers to manage or patch.
*   **End-to-End Reproducibility:** Every recommendation is fully auditable and reproducible. A `metadata.json` artifact is generated for each run, linking the output to the exact **code commit (Git)**, **data version (DVC)**, and **Docker image (ECR)** that produced it.
*   **Configuration-Driven:** New countries can be onboarded **without any code changes**. The entire pipeline is driven by country-specific `.yaml` configuration files.
*   **Robust, Constrained Optimization:** The core logic moves beyond the notebook's naïve assumptions. It maximizes an **expected net revenue** function that accounts for probabilistic jackpot payouts and secondary prize costs, while adhering to hard constraints like the 52-week payout ratio and a company cash safety net.
*   **Automated Testing & Deployment:** The CI/CD pipeline acts as a quality gate, running unit tests, contract tests on configurations, and deploying the infrastructure via AWS CDK.
*   **Secure by Design:** The architecture follows the principle of least privilege with granular IAM roles, encrypts all data at rest and in transit using KMS, and securely manages sensitive information like `available_cash` via **AWS Secrets Manager**.

---

### **3. End-to-End Workflow**

1.  **Trigger:** An EventBridge rule starts the Step Functions state machine every Wednesday at 8 PM UTC.
2.  **Orchestration:** The Step Function starts a parallel `Map` state, running an independent workflow for each country defined in the configuration.
3.  **Data Validation:** The first step for each country is a data quality check to ensure the weekly sales data is present and valid.
4.  **Train Model:** A SageMaker Training Job is launched. It uses the versioned `Dockerfile` and `src/train.py` script to train a sales prediction model.
5.  **Evaluate & Register:** A "quality gate" Lambda function evaluates the model's performance. If it meets the threshold, it is versioned and registered in the **SageMaker Model Registry** with an `Approved` status.
6.  **Optimize:** A Lambda function loads the latest `Approved` model from the registry. It runs the `src/optimise.py` script, checking all business constraints (payout ratio, cash safety net) to find and finalize the optimal jackpot.
7.  **Notify & Log:** The final recommendation is published to an **SNS topic** for stakeholder email notification. A `metadata.json` artifact is saved to S3 and indexed in DynamoDB to ensure full provenance.

---

### **4. Project Structure**

```
.
├── .github/workflows/          # GitHub Actions for CI/CD
├── configs/                    # Configuration files per country
├── data/                       # Data versioned with DVC
├── iac/                        # Infrastructure as Code (AWS CDK)
├── notebooks/                  # Exploratory notebooks (not deployed)
├── src/                        # Production source code
├── tests/                      # Unit and integration tests
├── .gitignore
├── Dockerfile
├── README.md
└── requirements.txt
```

---

### **5. Local Development Setup**

#### **Prerequisites**
- AWS Account & configured AWS CLI
- Python 3.9+
- Docker
- Node.js & AWS CDK
- DVC (Data Version Control)

#### **Setup Instructions**
1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd jackpot-optimizer
    ```
2.  **Set up the Python environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Install Jupytext for Notebook Sync:**
    This allows for a clean workflow between notebooks and `.py` scripts.
    ```bash
    pip install jupytext
    ```
4.  **Pull the data:**
    *Ensure your AWS credentials are configured for DVC to access the remote S3 storage.*
    ```bash
    dvc pull
    ```

#### **Running Locally**
- **Run unit tests:**
  ```bash
  pytest tests/
  ```
- **Run a local training job inside Docker:**
  ```bash
  docker build -t jackpot-optimizer .
  docker run -v $(pwd)/models:/app/models jackpot-optimizer src/train.py --config configs/england.yaml
  ```

---

### **6. Onboarding a New Country**

The process is designed to be code-free:
1.  **Add Config File:** Create a new `configs/<country_name>.yaml` file.
2.  **Add Data:** Ensure historical data for the new country is in `data/lottery_sales.csv.gz` and run `dvc add` to update the data pointer.
3.  **Update IaC:** Add the new country's name to the list in `iac/iac_stack.py`.
4.  **Commit & Push:** Commit the changes to Git. The CI/CD pipeline will automatically update the Step Functions workflow to include the new country.

---

### **7. Technology Stack & Justification**

| Component | Tool | Justification |
| :--- | :--- | :--- |
| **Orchestration** | **AWS Step Functions** | Serverless, native AWS integration, visual workflow, and robust error handling. Chosen over Airflow for its lower operational overhead for this linear batch use case. |
| **Data Versioning** | **DVC + S3** | DVC provides Git-centric, atomic versioning of data, which is crucial for reproducibility and is something S3 versioning alone cannot provide. |
| **Model Management** | **SageMaker Model Registry** | Provides a governed, versioned, and auditable central store for models with built-in lineage tracking and approval workflows. Chosen over MLflow for its seamless integration. |
| **CI/CD** | **GitHub Actions** | Industry standard for CI/CD, with secure OIDC integration for keyless authentication to AWS. |
| **Infrastructure** | **AWS CDK** | Allows defining infrastructure in Python, keeping the entire stack in one language and enabling more powerful abstractions than raw CloudFormation/Terraform. |
| **Compute** | **SageMaker Jobs & AWS Lambda** | Uses managed, serverless compute tailored to the task: SageMaker for heavy training and Lambda for lightweight, fast optimization logic. |
| **Security** | **IAM, KMS, Secrets Manager, VPC** | A defense-in-depth strategy: least-privilege roles, encryption everywhere with KMS, secure secret storage, and network isolation with a VPC. |
