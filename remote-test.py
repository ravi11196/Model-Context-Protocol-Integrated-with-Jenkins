import asyncio
import httpx
import json

# ============================================================
# CONFIGURATION
# ============================================================
MCP_URL = "https://jenkins-mcp.cloudfront.net/mcp-server/mcp"
API_KEY  = "-"

def get_base_headers():
    return {
        "x-api-key"      : API_KEY,
        "Content-Type"   : "application/json",
        "Accept"         : "application/json, text/event-stream",
        "Accept-Encoding": "identity",
    }

def get_session_headers(session_id: str):
    headers = get_base_headers()
    headers["mcp-session-id"] = session_id
    return headers

# ============================================================
# PARSERS
# ============================================================
def parse_sse_response(raw_text: str) -> list:
    results = []
    blocks  = raw_text.strip().split("\n\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        obj = json.loads(data_str)
                        results.append(obj)
                    except json.JSONDecodeError:
                        results.extend(parse_multi_json(data_str))
    return results

def parse_multi_json(raw_text: str) -> list:
    results = []
    decoder = json.JSONDecoder()
    idx     = 0
    text    = raw_text.strip()
    while idx < len(text):
        while idx < len(text) and text[idx] in ' \t\n\r':
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end_idx = decoder.raw_decode(text, idx)
            results.append(obj)
            idx = end_idx
        except json.JSONDecodeError:
            break
    return results

def parse_response(raw_text: str) -> list:
    text = raw_text.strip()
    if not text:
        return []
    if (text.startswith("id:")    or
        text.startswith("event:") or
        text.startswith("data:")):
        results = parse_sse_response(text)
        if results:
            return results
    if text.startswith("{") or text.startswith("["):
        return parse_multi_json(text)
    return parse_sse_response(text)

def find_result(objects: list, req_id: int):
    for obj in objects:
        if obj.get("id") == req_id and "result" in obj:
            return obj
    for obj in objects:
        if "result" in obj:
            return obj
    for obj in objects:
        if "error" in obj:
            return obj
    return None

# ============================================================
# EXTRACT CONTENT TEXT from tool result
# ============================================================
def extract_text(result: dict) -> str | None:
    """Pull the text string out of tools/call result content."""
    if not result or "result" not in result:
        return None
    content = result["result"].get("content", [])
    for item in content:
        text = item.get("text", "")
        if text:
            return text
    return None

def extract_json(result: dict):
    """Pull and parse JSON from tools/call result content."""
    text = extract_text(result)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

# ============================================================
# SCHEMA HELPERS
# ============================================================
def get_required_args(tool: dict) -> list:
    return tool.get("inputSchema", {}).get("required", [])

def get_all_arg_names(tool: dict) -> list:
    return list(tool.get("inputSchema", {}).get("properties", {}).keys())

def get_arg_type(tool: dict, arg_name: str) -> str:
    props = tool.get("inputSchema", {}).get("properties", {})
    return props.get(arg_name, {}).get("type", "string")

def get_arg_default(tool: dict, arg_name: str):
    props = tool.get("inputSchema", {}).get("properties", {})
    return props.get(arg_name, {}).get("default", None)

def print_tool_schema(tool: dict):
    name       = tool.get("name", "")
    desc       = tool.get("description", "No description")
    schema     = tool.get("inputSchema", {})
    properties = schema.get("properties", {})
    required   = schema.get("required", [])

    print(f"\n   {name}")
    print(f"     Desc     : {desc}")
    print(f"     Required : {required}")
    if properties:
        print(f"     Args     :")
        for prop_name, prop_info in properties.items():
            prop_type    = prop_info.get("type", "?")
            prop_desc    = prop_info.get("description", "")
            prop_default = prop_info.get("default", "—")
            req_marker   = "* " if prop_name in required else "  "
            print(f"       {req_marker}{prop_name:<22} [{prop_type:<8}] "
                  f"default={prop_default}  {prop_desc}")
    else:
        print(f"     Args     : (none)")

def pretty_print_result(result: dict, max_lines: int = 30):
    """Pretty print tool result, truncating if too long."""
    text = extract_text(result)
    if not text:
        print("  → (empty response)")
        return

    # Check if it's an error message from the tool
    if text.startswith("Error"):
        print(f"   Tool Error: {text[:300]}")
        return

    # Try pretty JSON
    try:
        parsed = json.loads(text)
        pretty = json.dumps(parsed, indent=2)
        lines  = pretty.split("\n")
        shown  = lines[:max_lines]
        print(f"  → (JSON, {len(lines)} lines)")
        for line in shown:
            print(f"     {line}")
        if len(lines) > max_lines:
            print(f"     ... ({len(lines) - max_lines} more lines truncated)")
    except (json.JSONDecodeError, TypeError):
        # Plain text
        print(f"  → {text[:400]}")

# ============================================================
# MCP REQUEST HELPER
# ============================================================
async def mcp_request(
    client    : httpx.AsyncClient,
    session_id: str,
    method    : str,
    params    : dict,
    req_id    : int,
) -> dict | None:

    headers = get_session_headers(session_id) if session_id else get_base_headers()
    payload = {
        "jsonrpc": "2.0",
        "id"     : req_id,
        "method" : method,
        "params" : params
    }

    try:
        resp = await client.post(
            MCP_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
    except httpx.RequestError as e:
        print(f"   Network Error: {e}")
        return None

    if resp.status_code not in [200, 202]:
        print(f"   HTTP {resp.status_code}: {resp.text[:200]}")
        return None

    objects = parse_response(resp.text)
    return find_result(objects, req_id)

# ============================================================
# STEP 1: Initialize
# ============================================================
async def initialize(client: httpx.AsyncClient) -> str | None:
    print("\n" + "="*60)
    print("STEP 1: Initialize")
    print("="*60)

    try:
        resp = await client.post(
            MCP_URL,
            headers=get_base_headers(),
            json={
                "jsonrpc": "2.0",
                "id"     : 1,
                "method" : "initialize",
                "params" : {
                    "protocolVersion": "2025-06-18",
                    "capabilities"   : {
                        "roots"   : {"listChanged": True},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name"   : "remote-mcp-client",
                        "version": "1.0.0"
                    }
                }
            },
            timeout=30
        )
    except httpx.RequestError as e:
        print(f"   Network Error: {e}")
        return None

    session_id = (
        resp.headers.get("mcp-session-id") or
        resp.headers.get("Mcp-Session-Id") or
        resp.headers.get("x-session-id")
    )

    if resp.status_code not in [200, 202]:
        print(f"   HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    objects = parse_response(resp.text)
    result  = find_result(objects, req_id=1)

    if result and "result" in result:
        info = result["result"]
        print(f"   Session ID  : {session_id}")
        print(f"   Protocol    : {info.get('protocolVersion', 'N/A')}")
        print(f"   Server      : {info.get('serverInfo', {}).get('name', 'N/A')} "
              f"v{info.get('serverInfo', {}).get('version', 'N/A')}")
        print(f"   Capabilities: {list(info.get('capabilities', {}).keys())}")
        return session_id or "no-session"
    else:
        print(f"   Parse failed: {objects[:2]}")
        return None

# ============================================================
# STEP 2: List Tools
# ============================================================
async def list_tools(
    client    : httpx.AsyncClient,
    session_id: str
) -> dict:
    """Returns {tool_name: tool_definition}"""
    print("\n" + "="*60)
    print("STEP 2: List Tools + Schemas")
    print("="*60)

    result = await mcp_request(
        client, session_id,
        method="tools/list",
        params={},
        req_id=2
    )

    if not result or "result" not in result:
        print(f"   Failed: {result}")
        return {}

    tools     = result["result"].get("tools", [])
    tools_map = {t["name"]: t for t in tools}

    print(f"\n  Total: {len(tools)} tools\n")
    for t in tools:
        print_tool_schema(t)

    return tools_map

# ============================================================
# CORE: call_tool with full validation
# ============================================================
async def call_tool(
    client    : httpx.AsyncClient,
    session_id: str,
    tool      : dict,
    arguments : dict,
    req_id    : int,
    label     : str = ""
) -> dict | None:

    tool_name = tool.get("name", "unknown")
    separator = f"── {label or tool_name} (req_id={req_id}) "
    print(f"\n{separator}{'─' * max(0, 58 - len(separator))}")

    # Validate: check all required args are present and non-empty
    required = get_required_args(tool)
    missing  = []
    for req_arg in required:
        val = arguments.get(req_arg)
        # Treat None and empty string as missing
        if val is None or val == "":
            missing.append(req_arg)

    if missing:
        print(f"    Skipping - missing required args: {missing}")
        print(f"     Tool needs: {required}")
        print(f"     Got       : {arguments}")
        return None

    # Validate: remove any args NOT in the schema
    all_known = get_all_arg_names(tool)
    if all_known:  # only filter if schema has defined properties
        unknown = [k for k in arguments if k not in all_known]
        if unknown:
            print(f"    Removing unknown args: {unknown}")
            arguments = {k: v for k, v in arguments.items() if k in all_known}

    print(f"  Args: {arguments}")

    result = await mcp_request(
        client, session_id,
        method="tools/call",
        params={"name": tool_name, "arguments": arguments},
        req_id=req_id
    )

    if not result or "result" not in result:
        print(f"   No result returned")
        return None

    content = result["result"].get("content", [])
    print(f"   HTTP OK | content items: {len(content)}")
    pretty_print_result(result)

    return result

# ============================================================
# MAIN FLOW
# ============================================================
async def run():
    print("\n Remote MCP Client")
    print(f" {MCP_URL}")
    print(f" API Key: {API_KEY[:8]}{'*' * (len(API_KEY) - 8)}")

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True
    ) as client:

        # ── Step 1: Initialize ────────────────────────────────
        session_id = await initialize(client)
        if not session_id:
            print("\n FATAL: Cannot initialize.")
            return

        # ── Step 2: List all tools + their schemas ────────────
        tools_map = await list_tools(client, session_id)
        if not tools_map:
            print("\n No tools returned.")
            return

        req_id = 10  # rolling request counter

        # ── Step 3: No-argument tools ─────────────────────────
        print("\n" + "="*60)
        print("STEP 3: Calling No-Argument Tools")
        print("="*60)

        no_arg_tools = [
            "whoAmI", "getStatus", "getHealth",
            "getVersion", "getNodes", "getViews",
            "getQueue", "getPlugins", "getExecutors",
        ]

        for name in no_arg_tools:
            if name in tools_map:
                await call_tool(
                    client, session_id,
                    tool      = tools_map[name],
                    arguments = {},
                    req_id    = req_id
                )
                req_id += 1

        # ── Step 4: getJobs → collect real job names ──────────
        print("\n" + "="*60)
        print("STEP 4: getJobs → discover real job names")
        print("="*60)

        job_names = []  # will populate from response

        if "getJobs" in tools_map:
            result = await call_tool(
                client, session_id,
                tool      = tools_map["getJobs"],
                arguments = {},           # uses server defaults: limit=10, skip=0
                req_id    = req_id
            )
            req_id += 1

            # Extract job names from response
            data = extract_json(result)
            if data:
                jobs = data.get("jobs", [])
                job_names = [j.get("name") for j in jobs if j.get("name")]
                print(f"\n   Found {len(job_names)} jobs: {job_names}")

        if not job_names:
            print("   No jobs found - skipping job-specific tools")
        else:
            # Use first job for single-job tools
            first_job = job_names[0]
            print(f"\n  Using job: '{first_job}' for job-specific calls")

            # ── Step 5: Job-specific tools ────────────────────
            print("\n" + "="*60)
            print(f"STEP 5: Job-Specific Tools (job='{first_job}')")
            print("="*60)

            # getJob
            if "getJob" in tools_map:
                await call_tool(
                    client, session_id,
                    tool      = tools_map["getJob"],
                    arguments = {"jobName": first_job},
                    req_id    = req_id
                )
                req_id += 1

            # getJobDetails - check what arg name it uses
            if "getJobDetails" in tools_map:
                tool     = tools_map["getJobDetails"]
                all_args = get_all_arg_names(tool)
                print(f"\n  getJobDetails args: {all_args}")
                # Build args using whatever name the schema defines
                job_arg  = next(
                    (a for a in all_args if "job" in a.lower() or "name" in a.lower()),
                    all_args[0] if all_args else None
                )
                args = {job_arg: first_job} if job_arg else {}
                await call_tool(
                    client, session_id,
                    tool      = tool,
                    arguments = args,
                    req_id    = req_id
                )
                req_id += 1

            # getLastBuildNumber
            if "getLastBuildNumber" in tools_map:
                tool     = tools_map["getLastBuildNumber"]
                all_args = get_all_arg_names(tool)
                print(f"\n  getLastBuildNumber args: {all_args}")
                # Find the job-name argument (whatever it's called)
                job_arg  = next(
                    (a for a in all_args if "job" in a.lower() or "name" in a.lower()),
                    all_args[0] if all_args else None
                )
                args = {job_arg: first_job} if job_arg else {}
                result = await call_tool(
                    client, session_id,
                    tool      = tool,
                    arguments = args,
                    req_id    = req_id
                )
                req_id += 1

                # Extract build number for next calls
                build_number = None
                if result:
                    data = extract_json(result)
                    if isinstance(data, dict):
                        build_number = (
                            data.get("number") or
                            data.get("buildNumber") or
                            data.get("lastBuild", {}).get("number")
                        )
                    elif isinstance(data, (int, str)):
                        build_number = int(data)
                    print(f"\n  Last build number: {build_number}")

                # ── Step 6: Build-specific tools ──────────────
                if build_number:
                    print("\n" + "="*60)
                    print(f"STEP 6: Build Tools (job='{first_job}', build={build_number})")
                    print("="*60)

                    # getBuild
                    if "getBuild" in tools_map:
                        tool     = tools_map["getBuild"]
                        all_args = get_all_arg_names(tool)
                        print(f"\n  getBuild args: {all_args}")
                        # Map args intelligently
                        args = build_args_for_tool(tool, first_job, build_number)
                        await call_tool(
                            client, session_id,
                            tool      = tool,
                            arguments = args,
                            req_id    = req_id
                        )
                        req_id += 1

                    # getBuildLog
                    if "getBuildLog" in tools_map:
                        tool = tools_map["getBuildLog"]
                        args = build_args_for_tool(tool, first_job, build_number)
                        await call_tool(
                            client, session_id,
                            tool      = tool,
                            arguments = args,
                            req_id    = req_id
                        )
                        req_id += 1

                    # getBuildChangeSets
                    if "getBuildChangeSets" in tools_map:
                        tool = tools_map["getBuildChangeSets"]
                        args = build_args_for_tool(tool, first_job, build_number)
                        await call_tool(
                            client, session_id,
                            tool      = tool,
                            arguments = args,
                            req_id    = req_id
                        )
                        req_id += 1

                    # getTestResults
                    if "getTestResults" in tools_map:
                        tool = tools_map["getTestResults"]
                        args = build_args_for_tool(tool, first_job, build_number)
                        await call_tool(
                            client, session_id,
                            tool      = tool,
                            arguments = args,
                            req_id    = req_id
                        )
                        req_id += 1

        print("\n" + "="*60)
        print(" ALL STEPS COMPLETE")
        print(f"   Session : {session_id}")
        print(f"   Tools   : {len(tools_map)} available")
        print(f"   Jobs    : {job_names}")
        print("="*60)


# ============================================================
# SMART ARG BUILDER for job+build tools
# ============================================================
def build_args_for_tool(
    tool        : dict,
    job_name    : str,
    build_number: int | None = None
) -> dict:
    """
    Intelligently map job_name and build_number to whatever
    argument names the tool's schema actually defines.

    Handles variations like:
      jobName / jobFullName / job_name / name / fullName
      buildNumber / build_number / number / buildId
    """
    all_args = get_all_arg_names(tool)
    required = get_required_args(tool)
    args     = {}

    # Keywords to detect job-name argument
    job_keywords   = ["jobfullname", "jobname", "job_name", "job",
                      "fullname", "name"]
    # Keywords to detect build-number argument
    build_keywords = ["buildnumber", "build_number", "number",
                      "buildid", "build_id", "build"]

    for arg in all_args:
        arg_lower = arg.lower()

        # Match job name
        if any(kw == arg_lower for kw in job_keywords):
            args[arg] = job_name
            continue

        # Match build number
        if build_number is not None:
            if any(kw == arg_lower for kw in build_keywords):
                # Cast to correct type
                arg_type = get_arg_type(tool, arg)
                args[arg] = int(build_number) if arg_type == "integer" else str(build_number)
                continue

        # Fill required args with defaults if we haven't matched them
        if arg in required and arg not in args:
            default = get_arg_default(tool, arg)
            if default is not None:
                args[arg] = default
            else:
                arg_type = get_arg_type(tool, arg)
                if arg_type == "integer":
                    args[arg] = 0
                elif arg_type == "boolean":
                    args[arg] = False
                else:
                    args[arg] = ""

    print(f"  Built args for {tool.get('name')}: {args}")
    return args


# ============================================================
# INTERACTIVE MODE
# ============================================================
async def interactive():
    """python remote_mcp_client.py interactive"""
    print("\n Remote MCP - Interactive Mode")
    print(f" {MCP_URL}\n")

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:

        session_id = await initialize(client)
        if not session_id:
            return

        tools_map = await list_tools(client, session_id)
        req_id    = 100

        print(f"\n\nAvailable tools: {list(tools_map.keys())}")
        print("Commands: <tool_name> | list | quit\n")

        while True:
            try:
                cmd = input("\nTool> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd.lower() in ["quit", "exit", "q"]:
                break

            if cmd.lower() == "list":
                print(f"Tools: {list(tools_map.keys())}")
                continue

            if cmd not in tools_map:
                print(f" Unknown: '{cmd}'")
                print(f"   Available: {list(tools_map.keys())}")
                continue

            tool     = tools_map[cmd]
            all_args = get_all_arg_names(tool)
            required = get_required_args(tool)
            print_tool_schema(tool)

            # Collect args interactively
            arguments = {}
            if all_args:
                print(f"\n  Enter values (* = required, blank = use default/skip):")
                for arg in all_args:
                    marker   = "* " if arg in required else "  "
                    arg_type = get_arg_type(tool, arg)
                    default  = get_arg_default(tool, arg)
                    hint     = f"default={default}" if default is not None else "no default"
                    val      = input(f"  {marker}{arg} [{arg_type}, {hint}]: ").strip()

                    if val:
                        if arg_type == "integer":
                            try:
                                arguments[arg] = int(val)
                            except ValueError:
                                print(f"    '{val}' is not an integer, using as string")
                                arguments[arg] = val
                        elif arg_type == "number":
                            try:
                                arguments[arg] = float(val)
                            except ValueError:
                                arguments[arg] = val
                        elif arg_type == "boolean":
                            arguments[arg] = val.lower() in ["true", "1", "yes", "y"]
                        else:
                            arguments[arg] = val
                    elif default is not None:
                        arguments[arg] = default
                        print(f"  → using default: {default}")

            await call_tool(
                client, session_id,
                tool      = tool,
                arguments = arguments,
                req_id    = req_id
            )
            req_id += 1

        print("\n Goodbye!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive())
    else:
        asyncio.run(run())
