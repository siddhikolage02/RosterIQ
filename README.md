# RosterIQ – Intelligent Workforce Management System

**RosterIQ** is an intelligent workforce management and roster scheduling application built with Python. It helps organizations manage employees, organize teams and processes, handle leave requests, automate workforce scheduling, and monitor operational performance through a centralized dashboard.

The application combines workforce management, scheduling optimization, reporting, role-based access control, and AI-powered assistance in one platform.

---

## Key Features

### 1. Dashboard & Workforce Analytics
- Centralized workforce overview.
- Employee and workforce statistics.
- Operational performance monitoring.
- Interactive data visualizations.

### 2. Employee Management
- Employee registration and profile management.
- Employee information updates.
- Employment status management.
- Role-based employee organization.

### 3. Roster Calendar
- Interactive workforce roster calendar.
- Employee shift and assignment management.
- Roster scheduling and editing.
- Calendar-based workforce visibility.

### 4. Leave & Availability Management
- Employee leave request management.
- Leave availability tracking.
- Leave status monitoring.
- Workforce availability management.

### 5. Pods & Processes Management
- Organize employees into operational pods.
- Manage brands and business processes.
- Associate employees with organizational structures.
- Maintain workforce allocation information.

### 6. Approval Management
- Centralized approval workflow.
- Review and process roster approvals.
- Track approval activities.
- Maintain audit records of important changes.

### 7. Reports & Analytics
- Workforce and operational reporting.
- Structured data summaries.
- Performance insights.
- Reporting support for workforce decisions.

### 8. AI Assistant – Amazon Bedrock
RosterIQ includes an AI-powered workforce assistant integrated with **Amazon Bedrock**.

Key capabilities:
- AI-powered natural-language interaction.
- Workforce-related question assistance.
- Integration with Amazon Bedrock foundation models.
- Configurable AWS region and Bedrock model.
- Secure AWS authentication through configured AWS credentials.

The AI Assistant is designed to make workforce information and operational assistance more accessible through conversational interaction.

---

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Frontend | Streamlit |
| Backend | Python |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data Processing | Pandas |
| Data Visualization | Plotly |
| Scheduling Optimization | Google OR-Tools |
| AI Integration | Amazon Bedrock |
| AWS SDK | Boto3 |
| Authentication | Python, Bcrypt |
| Testing | Pytest |
| Version Control | Git & GitHub |

---

## Project Architecture

```text
RosterIQ/
│
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
├── src/
│   ├── ai/
│   │
│   ├── auth/
│   │   ├── auth_service.py
│   │   ├── password_service.py
│   │   └── permission_service.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── init_db.py
│   │   ├── models.py
│   │   ├── seed_data.py
│   │   └── seed_calendar_data.py
│   │
│   ├── scheduling/
│   │   ├── backup_recommendation_service.py
│   │   ├── eligibility_service.py
│   │   ├── roster_edit_service.py
│   │   ├── roster_generator.py
│   │   └── validation_service.py
│   │
│   ├── services/
│   │   ├── ai_assistant_service.py
│   │   ├── approval_service.py
│   │   ├── assignment_service.py
│   │   ├── audit_service.py
│   │   ├── brand_service.py
│   │   ├── calendar_service.py
│   │   ├── employee_service.py
│   │   ├── leave_service.py
│   │   ├── organization_service.py
│   │   ├── pod_service.py
│   │   ├── process_service.py
│   │   ├── report_service.py
│   │   └── roster_service.py
│   │
│   ├── ui/
│   ├── utils/
│   │
│   └── views/
│       ├── ai_assistant.py
│       ├── approvals.py
│       ├── dashboard.py
│       ├── employees.py
│       ├── layout.py
│       ├── leave_availability.py
│       ├── pods_processes.py
│       ├── reports.py
│       └── roster_calendar.py
│
└── tests/
    ├── integration/
    ├── unit/
    ├── conftest.py
    ├── test_approval_service.py
    ├── test_audit_service.py
    ├── test_auth_service.py
    ├── test_database.py
    └── test_organization_service.py
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or later.
- Git.
- AWS account (for Amazon Bedrock functionality).
- Access to an eligible Amazon Bedrock foundation model.

### 1. Clone the repository

```bash
git clone https://github.com/siddhikolage02/RosterIQ.git
cd RosterIQ
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file using `.env.example` as a reference.

Configure the relevant AWS settings:

```env
AWS_REGION=ap-south-1
BEDROCK_MODEL_ID=your-bedrock-model-id
```

Use AWS CLI or an appropriately configured IAM role or profile for AWS credentials. Never store AWS access keys or secret keys in your source code or commit them to GitHub.

### 5. Launch the application

```powershell
streamlit run app.py
```

The application will open in your browser.

---

## AWS Bedrock Configuration

RosterIQ uses Amazon Bedrock for its AI Assistant functionality.

To configure the integration:

1. Sign in to the AWS Management Console.
2. Open Amazon Bedrock.
3. Select an available foundation model.
4. Enable the required model access where applicable.
5. Configure AWS credentials using an appropriate IAM identity.
6. Set `AWS_REGION` and `BEDROCK_MODEL_ID` in your environment configuration.

The application uses Boto3 to communicate with Amazon Bedrock.

**Security recommendation:** Use IAM roles or temporary credentials wherever possible. Do not expose AWS credentials in GitHub repositories.

---

## Running Tests

Run the project test suite using:

```powershell
pytest -v
```

For test coverage:

```powershell
pytest --cov=src --cov-report=term-missing
```

---

## Security & Access Management

RosterIQ incorporates:
- Password hashing using Bcrypt.
- Authentication and authorization services.
- Role-based access control.
- Organization-level access restrictions.
- Audit logging for important workforce activities.
- Environment-based configuration for sensitive settings.

---

## Future Enhancements

- Advanced AI-driven workforce recommendations.
- Enhanced roster optimization.
- Cloud database integration.
- AWS deployment and hosting.
- Advanced workforce forecasting.
- Expanded reporting and analytics.

---

## Author

**Siddhi Kolage**

Artificial Intelligence & Data Science Engineer

**GitHub:** [@siddhikolage02](https://github.com/siddhikolage02)

**Project Repository:** [RosterIQ](https://github.com/siddhikolage02/RosterIQ)

---

*RosterIQ – Smarter Workforce Management. Better Scheduling. Intelligent Decisions.*
