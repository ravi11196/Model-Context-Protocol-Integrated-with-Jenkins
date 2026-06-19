import requests


def register_tools(mcp, JENKINS_URL, auth, get_crumb):

    # ============================================================
    # 1. whoAmI
    # ============================================================

    @mcp.tool()
    def whoAmI():

        url = f"{JENKINS_URL}/me/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 2. getStatus
    # ============================================================

    @mcp.tool()
    def getStatus():

        url = f"{JENKINS_URL}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        return {
            "mode": data.get("mode"),
            "nodeDescription": data.get("nodeDescription"),
            "numExecutors": data.get("numExecutors"),
            "quietingDown": data.get("quietingDown"),
            "useCrumbs": data.get("useCrumbs"),
            "useSecurity": data.get("useSecurity")
        }

    # ============================================================
    # 3. getJobs
    # ============================================================

    @mcp.tool()
    def getJobs(limit: int = 10, skip: int = 0):

        url = f"{JENKINS_URL}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        jobs = data.get("jobs", [])

        return {
            "jobs": jobs[skip: skip + limit]
        }

    # ============================================================
    # 4. getJob
    # ============================================================

    @mcp.tool()
    def getJob(jobFullName: str):

        url = f"{JENKINS_URL}/job/{jobFullName}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 5. getJobDetails
    # ============================================================

    @mcp.tool()
    def getJobDetails(name: str):

        url = f"{JENKINS_URL}/job/{name}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 6. triggerBuild
    # ============================================================

    @mcp.tool()
    def triggerBuild(jobFullName: str):

        url = f"{JENKINS_URL}/job/{jobFullName}/build"

        r = requests.post(
            url,
            auth=auth(),
            headers=get_crumb()
        )

        return {
            "job": jobFullName,
            "status_code": r.status_code,
            "success": r.status_code in [200, 201, 202]
        }

    # ============================================================
    # 7. buildJob
    # ============================================================

    @mcp.tool()
    def buildJob(name: str):

        url = f"{JENKINS_URL}/job/{name}/build"

        r = requests.post(
            url,
            auth=auth(),
            headers=get_crumb()
        )

        return {
            "job": name,
            "status_code": r.status_code,
            "success": r.status_code in [200, 201, 202]
        }

    # ============================================================
    # 8. getBuild
    # ============================================================

    @mcp.tool()
    def getBuild(jobFullName: str, buildNumber: int = None):

        if buildNumber:
            url = f"{JENKINS_URL}/job/{jobFullName}/{buildNumber}/api/json"
        else:
            url = f"{JENKINS_URL}/job/{jobFullName}/lastBuild/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 9. getBuildLog
    # ============================================================

    @mcp.tool()
    def getBuildLog(
        jobFullName: str,
        buildNumber: int = None,
        limit: int = 50
    ):

        if buildNumber:
            url = f"{JENKINS_URL}/job/{jobFullName}/{buildNumber}/consoleText"
        else:
            url = f"{JENKINS_URL}/job/{jobFullName}/lastBuild/consoleText"

        r = requests.get(
            url,
            auth=auth()
        )

        lines = r.text.splitlines()

        return {
            "lines": lines[-limit:],
            "hasMore": len(lines) > limit
        }

    # ============================================================
    # 10. getBuildChangeSets
    # ============================================================

    @mcp.tool()
    def getBuildChangeSets(
        jobFullName: str,
        buildNumber: int = None
    ):

        if buildNumber:
            url = f"{JENKINS_URL}/job/{jobFullName}/{buildNumber}/api/json"
        else:
            url = f"{JENKINS_URL}/job/{jobFullName}/lastBuild/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        return data.get("changeSets", [])

    # ============================================================
    # 11. getTestResults
    # ============================================================

    @mcp.tool()
    def getTestResults(
        jobFullName: str,
        buildNumber: int = None
    ):

        if buildNumber:
            url = f"{JENKINS_URL}/job/{jobFullName}/{buildNumber}/testReport/api/json"
        else:
            url = f"{JENKINS_URL}/job/{jobFullName}/lastBuild/testReport/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        if r.status_code != 200:
            return {
                "passCount": 0,
                "failCount": 0,
                "skipCount": 0,
                "totalCount": 0
            }

        data = r.json()

        return {
            "passCount": data.get("passCount", 0),
            "failCount": data.get("failCount", 0),
            "skipCount": data.get("skipCount", 0),
            "totalCount": data.get("totalCount", 0)
        }

    # ============================================================
    # 12. getNodes
    # ============================================================

    @mcp.tool()
    def getNodes():

        url = f"{JENKINS_URL}/computer/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 13. getViews
    # ============================================================

    @mcp.tool()
    def getViews():

        url = f"{JENKINS_URL}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        return data.get("views", [])

    # ============================================================
    # 14. getQueue
    # ============================================================

    @mcp.tool()
    def getQueue():

        url = f"{JENKINS_URL}/queue/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 15. getPlugins
    # ============================================================

    @mcp.tool()
    def getPlugins():

        url = f"{JENKINS_URL}/pluginManager/api/json?depth=1"

        r = requests.get(
            url,
            auth=auth()
        )

        return r.json()

    # ============================================================
    # 16. getExecutors
    # ============================================================

    @mcp.tool()
    def getExecutors():

        url = f"{JENKINS_URL}/computer/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        return data.get("computer", [])

    # ============================================================
    # 17. getLastBuildNumber
    # ============================================================

    @mcp.tool()
    def getLastBuildNumber(jobFullName: str):

        url = f"{JENKINS_URL}/job/{jobFullName}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        return {
            "lastBuild": data.get("lastBuild", {})
        }

    # ============================================================
    # 18. getHealth
    # ============================================================

    @mcp.tool()
    def getHealth(jobFullName: str):

        url = f"{JENKINS_URL}/job/{jobFullName}/api/json"

        r = requests.get(
            url,
            auth=auth()
        )

        data = r.json()

        return data.get("healthReport", [])

    # ============================================================
    # 19. getVersion
    # ============================================================

    @mcp.tool()
    def getVersion():

        r = requests.get(
            JENKINS_URL,
            auth=auth()
        )

        return {
            "version": r.headers.get("X-Jenkins")
        }

# ============================================================
    # 20. createUser
    # ============================================================

    @mcp.tool()
    def createUser(username: str, password: str, confirm: bool = False):

        if not confirm:
            return {"error": "confirm=True required to create user"}

        url = f"{JENKINS_URL}/securityRealm/createAccount"

        r = requests.post(
            url,
            auth=auth(),
            headers=get_crumb(),
            data={
                "username": username,
                "password1": password,
                "password2": password,
                "fullname": username,
                "email": f"{username}@example.com"
            }
        )

        return {
            "username": username,
            "status_code": r.status_code,
            "success": r.status_code in [200, 201, 302]
        }


    # ============================================================
    # 21. createPipeline
    # ============================================================

    @mcp.tool()
    def createPipeline(name: str, script: str, confirm: bool = False):

        if not confirm:
            return {"error": "confirm=True required to create pipeline"}

        url = f"{JENKINS_URL}/createItem?name={name}"

        config_xml = f"""
        <flow-definition plugin="workflow-job">
            <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition">
                <script>{script}</script>
                <sandbox>true</sandbox>
            </definition>
        </flow-definition>
        """

        r = requests.post(
            url,
            auth=auth(),
            headers={
                **get_crumb(),
                "Content-Type": "application/xml"
            },
            data=config_xml.encode("utf-8")
        )

        return {
            "job": name,
            "status_code": r.status_code,
            "success": r.status_code in [200, 201]
        }


    # ============================================================
    # 22. updatePipeline
    # ============================================================

    @mcp.tool()
    def updatePipeline(name: str, script: str, confirm: bool = False):

        if not confirm:
            return {"error": "confirm=True required to update pipeline"}

        url = f"{JENKINS_URL}/job/{name}/config.xml"

        config_xml = f"""
        <flow-definition plugin="workflow-job">
            <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition">
                <script>{script}</script>
                <sandbox>true</sandbox>
            </definition>
        </flow-definition>
        """

        r = requests.post(
            url,
            auth=auth(),
            headers={
                **get_crumb(),
                "Content-Type": "application/xml"
            },
            data=config_xml.encode("utf-8")
        )

        return {
            "job": name,
            "status_code": r.status_code,
            "success": r.status_code in [200, 201]
        }
