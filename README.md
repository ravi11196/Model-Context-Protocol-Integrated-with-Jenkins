******************************Model Context Protocol Integrated with Jenkins******************************

**Overview**

This project demonstrates how to integrate Model Context Protocol (MCP) with Jenkins to enable intelligent, automated interaction with Jenkins pipelines.
The MCP proxy acts as a middleware layer that:
  - Exposes Jenkins capabilities via structured APIs
  - Enables AI or external systems to interact with Jenkins
  - Standardizes communication using MCP principles

Why MCP with Jenkins?
By integrating MCP:
    - AI agents can trigger and monitor Jenkins jobs
    - CI/CD pipelines can be controlled programmatically
    - Build insights (status/logs) become easily accessible
    - External systems can integrate seamlessly

**Prerequisites:-**

Ensure the following tools are installed:
- Python3 3.11.15
- Docker
- Docker Compose
- Git

**************************************************Project Structure**************************************************

  **1) functions.py**

  Core logic layer for Jenkins interaction
  Handles:
  - Job triggering
  - Build status retrieval
  - Logs fetching
  - Acts as a service layer between proxy and Jenkins

  **2) proxy_mcp.py**

  Main entry point of MCP proxy
  - Handles incoming requests
  - Routes calls to functions.py
  - Formats MCP-compatible responses

  **3) remote-test.py**

  Test script to validate MCP endpoints
  - Simulates remote API calls
  - Useful for debugging

  **4) requirements.txt**

  Lists Python dependencies
  - Used for container build and local setup

  **5) Dockerfile**

  Builds container image
  - Installs dependencies and runtime environment

  **6) docker-compose.yaml**

  Defines services and configurations
  - Manages container orchestration

  **7) .env**

  Stores environment-specific configurations:
  - Jenkins URL
  - Credentials / API tokens
  -  Other runtime configs

**************************************************Installation & Setup**************************************************

  **- Clone Repository**

  'git clone https://github.com/ravi11196/Model-Context-Protocol-Integrated-with-Jenkins.git'

  **- Navigate to Directory**

  'cd Model-Context-Protocol-Integrated-with-Jenkins'

  **- Build Docker Image**

  'docker build --no-cache -t jenkins-mcp-proxy .'

  **- Start Services**

  'docker compose up -d'
*********************************************Verification & Health Check*************************************************

  **- Check Running Containers**

  'docker ps'

  **- View Logs**

  'docker compose logs -f'
  or

  'docker logs <container_name>'

  **- Health Validation**

  Verify the following in logs:
   - MCP proxy server started successfully
   - Jenkins connection established
   - No authentication errors
   - Health check endpoint responding (if configured)

**************************************************Testing**************************************************

  **Run the test script:**

  'python3 remote-test.py'

  This will:
   - Send test requests to MCP proxy
   - Validate responses
   - Confirm Jenkins integration

  **Use Cases**

   - AI-powered DevOps automation
   - Remote Jenkins orchestration
   - Build monitoring & reporting
   - Integration with LLM-based tools









