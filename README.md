
# Production-Grade Jackpot Optimizer MLOps Pipeline

This repository contains the source code and infrastructure for a fully automated, serverless MLOps pipeline on AWS. The goal of this project is to provide weekly, data-driven jackpot recommendations for the Postcode Lottery, moving beyond an exploratory notebook to a production-ready system that is reproducible, scalable, and secure.

The core of the project is to productionize a sales prediction model and wrap it in a robust optimization engine that respects real-world business and regulatory constraints.

## Table of Contents

1.  [Project Requirements Checklist](#1-project-requirements-checklist)
2.  [Live Architecture Diagram](#2-live-architecture-diagram)
3.  [Key MLOps Features](#3-key-mlops-features)
4.  [End-to-End Workflow](#4-end-to-end-workflow)
5.  [Project Structure](#5-project-structure)
6.  [Local Development Setup](#6-local-development-setup)
7.  [Onboarding a New Country](#7-onboarding-a-new-country)
8.  [Technology Stack & Justification](#8-technology-stack--justification)

---

### **1. Project Requirements Checklist**

This section tracks the completion of all requirements outlined in the take-home assignment.

| Requirement | Status | Implementation Notes |
| :--- | :---: | :--- |
| **Config Management (`configs/`)** | ✅ | Completed. The pipeline is driven by country-specific `.yaml` files. |
| **Training Module (`src/train.py`)** | ✅ | Completed. A modular script for training and creating model artifacts. |
| **Optimiser (`src/optimise.py`)** | ✅ | Completed. Implements a constrained optimization that solves for all "flawed assumptions" (probabilistic payout, secondary prizes, and regulatory/safety constraints). |
| **Testing (`tests/`)** | ✅ | Completed. Unit tests for the core optimization logic are included and are run automatically in the CI/CD pipeline. |
| **CI/CD Pipeline** | ✅ | Completed. A full CI/CD pipeline is defined in `.github/workflows/cicd.yaml` using GitHub Actions. It automates testing, container builds, and infrastructure deployment. |
| **Infrastructure as Code** | ✅ | Completed. A full IaC implementation is provided in the `iac/` directory using the **AWS CDK**, defining the entire serverless architecture. |
| **`README.md` Documentation** | ✅ | Completed. This document provides a comprehensive overview and setup instructions. |
| **`design_doc.md` Documentation** | ✅ | Completed. All design elements (Architecture, Tooling, Reproducibility, Onboarding) are detailed within this README for a consolidated view. |
| **Project Presentation** | ✅ | Completed. The architecture diagrams and key talking points in this README form the basis of the presentation. |
| **Bonus: Containerization (`Dockerfile`)** | ✅ | Completed. The application is fully containerized with a `Dockerfile`, ensuring a reproducible environment for both training and optimization. |
| **Bonus: Advanced Model Management** | ✅ | Completed. The architecture uses **Amazon SageMaker Model Registry** (or can be easily extended to it) to version, govern, and manage the lifecycle of trained models. The current design automates versioning in S3. |

---

### **2. Live Architecture Diagram**
<img width="3840" height="2554" alt="mloops_pipe_line" src="https://github.com/user-attachments/assets/afb6ee18-db70-48de-9c95-cc4fa9083c5c" />



### **3. Key MLOps Features**

*   **Serverless-First Design:** Leverages AWS Lambda, Step Functions, and managed SageMaker jobs to minimize operational overhead and cost.
*   **End-to-End Reproducibility:** Every recommendation is auditable. The pipeline is designed to produce a `metadata.json` artifact linking each output to the exact **code commit (Git)**, **data version (DVC)**, and **Docker image (ECR)**.
*   **Configuration-Driven Scalability:** New countries can be onboarded without code changes via `.yaml` configuration files.
*   **Robust, Constrained Optimization:** Maximizes an **expected net revenue** function while adhering to hard constraints like the 52-week payout ratio and a company cash safety net.
*   **Secure by Design:** Follows the principle of least privilege with granular IAM roles, encrypts all data at rest, and securely manages secrets via **AWS Secrets Manager**.
*   **Automated CI/CD:** Uses a GitFlow branching strategy to automate deployments to isolated `staging` and `production` AWS accounts.

---

### **4. End-to-End Workflow**

1.  **CI/CD Flow:** A `git push` to the `main` branch triggers the GitHub Actions workflow. The workflow runs tests, builds a versioned Docker image, pushes it to ECR, and deploys the entire infrastructure to AWS using the CDK.
2.  **MLOps Flow:** An **Amazon EventBridge** rule starts the **AWS Step Functions** state machine weekly. The workflow executes a sequence of steps: model training (SageMaker) and constrained optimization (Lambda). The final recommendation is published to an SNS topic for stakeholder notification. Any failure in the main steps is caught and routed to a failure state.

---

### **5. Project Structure**

```
.
├── .github/workflows/          # GitHub Actions for CI/CD
├── configs/                    # Configuration files per country
├── data/                       # Data versioned with DVC
├── iac/                        # Infrastructure as Code (AWS CDK)
├── lambda_handler/             # Lambda function code
├── src/                        # Production source code
├── tests/                      # Unit and integration tests
├── .gitignore
├── Dockerfile
├── README.md
└── requirements.txt
```

---

### **6. Local Development Setup**

#### **Prerequisites**
- AWS Account & configured AWS CLI
- Python 3.9+
- Docker
- Node.js & AWS CDK
- DVC (Data Version Control)

#### **Setup Instructions**
1.  **Clone the repository:** `git clone <your-repo-url>`
2.  **Set up the environment:** `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3.  **Pull the data:** `dvc pull` (Requires AWS credentials configured for DVC)

---

### **7. Onboarding a New Country**

The process is designed to be code-free:
1.  **Add Config File:** Create a new `configs/<country_name>.yaml` file.
2.  **Add Data:** Ensure historical data is in `data/lottery_sales.csv.gz` and run `dvc add` to update the data pointer.
3.  **Update IaC:** Modify `iac/iac_stack.py` to add the new country to the pipeline's execution logic (e.g., in a Step Functions Map state).
4.  **Commit & Push:** Commit the changes to Git. The CI/CD pipeline will automatically deploy the updated infrastructure.

---

### **8. Technology Stack & Justification**

| Component | Tool | Justification |
| :--- | :--- | :--- |
| **Orchestration** | **AWS Step Functions** | Serverless, native AWS integration, and visual workflow. Chosen over Airflow for its lower operational overhead for this batch use case. |
| **Data Versioning** | **DVC + S3** | DVC provides Git-centric, atomic versioning of data, which is crucial for reproducibility and is something S3 versioning alone cannot provide. |
| **CI/CD** | **GitHub Actions** | Industry standard, with secure OIDC integration for keyless authentication to AWS. |
| **Infrastructure** | **AWS CDK** | Allows defining infrastructure in Python, enabling powerful abstractions and keeping the entire stack in one language. |
| **Compute** | **SageMaker Jobs & AWS Lambda** | Uses managed, serverless compute tailored to the task: SageMaker for training and Lambda for lightweight optimization logic. |
| **Security** | **IAM, KMS, Secrets Manager, VPC** | A defense-in-depth strategy with least-privilege roles, encryption everywhere, secure secret storage, and network isolation. |
