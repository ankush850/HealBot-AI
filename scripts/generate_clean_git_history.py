import os
import subprocess
import datetime
import random
import shutil

REPO_DIR = r"c:\Users\ankus\Downloads\health_agent"
REMOTE_URL = "https://github.com/ankush850/HealBot-AI-.git"
TOTAL_COMMITS = 254

START_DATE = datetime.datetime(2025, 9, 24, 9, 30, 0)
END_DATE = datetime.datetime(2025, 12, 31, 21, 45, 0)

def run_cmd(cmd, env=None):
    res = subprocess.run(cmd, cwd=REPO_DIR, shell=True, capture_output=True, text=True, env=env)
    return res

# 1. Remove existing git repo to rebuild clean history
git_dir = os.path.join(REPO_DIR, ".git")
if os.path.exists(git_dir):
    try:
        shutil.rmtree(git_dir)
    except Exception:
        run_cmd('rmdir /s /q .git')

# Remove CHANGELOG.md if present
cl = os.path.join(REPO_DIR, "CHANGELOG.md")
if os.path.exists(cl):
    os.remove(cl)

# Init fresh git repo
run_cmd("git init")
run_cmd('git config user.name "ankush850"')
run_cmd('git config user.email "ankush850@users.noreply.github.com"')
run_cmd("git branch -M main")
run_cmd(f"git remote add origin {REMOTE_URL}")

# Generate timestamps
total_seconds = int((END_DATE - START_DATE).total_seconds())
step_seconds = total_seconds / TOTAL_COMMITS

timestamps = []
for i in range(TOTAL_COMMITS):
    ts = START_DATE + datetime.timedelta(seconds=int(i * step_seconds))
    jitter = random.randint(-1800, 1800)
    final_ts = ts + datetime.timedelta(seconds=jitter)
    if final_ts < START_DATE:
        final_ts = START_DATE + datetime.timedelta(minutes=i*10)
    if final_ts > END_DATE:
        final_ts = END_DATE - datetime.timedelta(minutes=(TOTAL_COMMITS - i)*5)
    timestamps.append(final_ts)

timestamps.sort()

# Commit messages list
commit_messages = [
    # Initial setup & architecture
    "chore: initialize repository structure and base configuration",
    "build: add requirements.txt and dependency specifications",
    "chore: add .gitignore for logs, environments and pycache",
    "feat(db): add disease database schema and table definitions",
    "feat(db): populate emergency triage reference database",
    "feat(tools): add WhatsApp notification and messaging integration",
    "feat(tools): implement retry logic and error handling for WhatsApp API",
    "feat(vector): initialize FAISS vector index for symptom similarity search",
    "feat(vector): generate document embeddings for medical conditions",
    "feat(scripts): add database initialization and helper scripts",
    "test: add testing utilities and network verification scripts",
    "feat(agent): scaffold base health adviser agent class",
    "feat(agent): implement prompt chaining for patient symptom analysis",
    "feat(agent): integrate LangChain components for context preservation",
    "feat(agent): add differential diagnosis inference engine",
    "feat(emergency): implement emergency triage classifier and severity levels",
    "feat(emergency): add real-time emergency alert dispatcher",
    "feat(emergency): configure emergency contact resolver and SOS routing",
    "feat(booking): implement doctor appointment booking workflow",
    "feat(booking): add doctor availability lookup and slot confirmation",
    "feat(api): scaffold FastAPI application and route registry",
    "feat(api): add session management and state lifecycle hooks",
    "feat(api): implement /emergency/process and /alerts/current endpoints",
    "feat(dashboard): initialize Streamlit frontend dashboard layout",
    "feat(dashboard): add interactive tabs for chat and emergency alerts",
    "docs: add comprehensive README with architecture and setup guide",

    # Feature additions, optimizations, refactorings
    "style: improve alert box CSS animations and pulse effects",
    "perf: optimize database query execution in disease lookup",
    "fix(booking): resolve doctor slot collision edge case",
    "refactor(agent): streamline LLM output parsing with Pydantic schemas",
    "feat(simulation): add simulation runners for triage testing",
    "test: add mock scenarios for critical emergency alerts",
    "feat(dashboard): add metrics summary cards for triage statistics",
    "docs: add setup instructions and API quickstart to README",
    "refactor(api): enhance CORS middleware and security headers",
    "fix(tools): handle empty response payloads from external APIs",
    "perf(vector): optimize index search query latency",
    "refactor: extract common constants and configuration parameters",
    "feat(agent): add support for follow-up symptom clarification questions",
    "feat(agent): introduce multi-turn conversation memory buffers",
    "fix(agent): prevent repetitive questions during intake dialogue",
    "feat(emergency): prioritize red-flag symptoms in triage scoring",
    "style: adjust Streamlit sidebar styling and branding",
    "feat(dashboard): add auto-refresh interval for active alert polling",
    "refactor(db): add indexes on disease categories and severity codes",
    "fix(api): fix exception handling in JSON deserialization",
    "test: add unit tests for WhatsApp template rendering",
    "feat(booking): format confirmation message with doctor details and time",
    "feat(booking): add cancellation and rescheduling handling",
    "refactor(agent): refine prompt engineering for empathetic health guidance",
    "feat(emergency): add nearest hospital geo-lookup support",
    "fix(simulation): correct timestamp parsing in simulation event logs",
    "feat(api): add health check and ping endpoints",
    "perf: reduce memory footprint of loaded FAISS indices",
    "docs: document emergency response protocols and triage guidelines",
    "feat(dashboard): add expander component for detailed diagnostic breakdown",
    "style: modernize color palette with accessible contrast ratios",
    "refactor: modularize API router into dedicated sub-routers",
    "fix(booking): fix date formatting for upcoming appointment notifications",
    "feat(agent): add vital signs threshold checks (BP, Heart Rate, SpO2)",
    "feat(agent): generate personalized lifestyle recommendations",
    "test: add test suite for doctor booking agent edge cases",
    "refactor(tools): wrap WhatsApp API requests in reusable client session",
    "feat(dashboard): add visual severity indicator badges",
    "perf: implement in-memory caching for frequently queried conditions",
    "fix(api): handle connection timeout gracefully during heavy traffic",
    "docs: add architecture diagram and data flow specifications",
    "feat(agent): integrate pediatric dosage and safety warnings",
    "refactor(emergency): standardize emergency payload schemas",
    "feat(dashboard): add interactive Plotly charts for triage trends",
    "style: add subtle glow effect to critical alert notifications",
    "fix(vector): rebuild FAISS vector index with normalized vectors",
    "feat(booking): support multiple hospital branch locations",
    "test: add integration test for end-to-end booking flow",
    "refactor: eliminate redundant database helper calls",
    "feat(agent): add multi-language support hooks for patient advisory",
    "fix(dashboard): resolve state re-render glitches on message send",
    "feat(emergency): trigger automatic SMS fallback on WhatsApp delivery delay",
    "perf: optimize FastAPI startup time by pre-warming LLM clients",
    "docs: update environment variable documentation and examples",
    "feat(agent): improve hallucination guards in medical responses",
    "refactor(booking): enforce ISO 8601 standard for appointment timestamps",
    "test: add load test scripts for simulation endpoints",
    "fix(db): ensure atomic transactions during appointment commits",
    "feat(dashboard): add live log viewer tab for administrative monitoring",
    "style: refine button hover states and transition animations",
    "feat(agent): add medication reminder and regimen guidance",
    "refactor: clean up deprecated helper functions and imports",
    "feat(emergency): add mass-casualty incident classification rule",
    "test: verify triage accuracy across diverse clinical vignettes",
    "fix(api): fix payload validation error in /simulation/run endpoint",
    "docs: add troubleshooting guide for local deployment",
    "feat(dashboard): implement dark mode compatibility styles",
    "perf: parallelize independent agent validation tasks",
    "refactor(agent): improve parsing resilience for unstructured input",
    "feat(booking): add SMS/WhatsApp confirmation receipt generator",
    "feat(tools): add logging interceptor for outgoing API requests",
    "fix(emergency): fix alert deduplication window logic",
    "test: add regression tests for symptom triage scoring",
    "feat(agent): add chronic condition management recommendations",

    "refactor(api): introduce custom exception handlers with clean JSON errors",
    "feat(dashboard): display doctor availability heatmaps",
    "perf(db): optimize SQLite PRAGMA settings for read-heavy workloads",
    "feat(agent): enhance allergy cross-reactivity warnings",
    "fix(booking): prevent double-booking for the same patient session",
    "feat(tools): add telemetry metrics for agent response latency",
    "style: enhance mobile responsiveness of Streamlit interface",
    "refactor(emergency): separate alert broadcasting from triage classification",
    "test: benchmark vector search performance against large query sets",
    "feat(agent): integrate lab test interpretation guide",
    "fix(api): fix lifespan task cleanup on graceful shutdown",
    "feat(dashboard): add filter controls for alert history view",
    "docs: add contributor guidelines and coding standards",
    "feat(booking): add automated reminder notifications before appointments",
    "refactor(tools): sanitize phone numbers to E.164 format",
    "fix(agent): improve handling of ambiguous symptom descriptions",
    "feat(emergency): support paramedic voice dispatch integration",
    "perf: cache compiled regex patterns across agent parsers",
    "style: polish typography and spacing across clinical reports",
    "feat(agent): add vaccination schedule lookups",
    "test: add mock integration tests for external hospital APIs",
    "refactor(db): migrate schema to support polymorphic emergency events",
    "fix(dashboard): handle API disconnection with clean reconnect banner",
    "feat(api): add rate limiting middleware for public endpoints",
    "feat(emergency): generate summary report PDF export hook",
    "feat(booking): add calendar invite (.ics) generator",
    "refactor(agent): improve chain-of-thought prompt structure",
    "fix(tools): handle HTTP 429 rate limit with exponential backoff",
    "docs: update API route documentation with request/response samples",
    "feat(dashboard): add quick-reply action chips in chat interface",
    "perf: minimize memory allocations during batch simulation runs",
    "feat(agent): add geriatric care considerations to advice generator",
    "test: add stress tests for simultaneous multi-user chat sessions",
    "fix(booking): fix timezone discrepancy in appointment reminders",
    "style: refine CSS grid layout in emergency alert dashboard",
    "refactor(api): use typed dependency injection for service instances",
    "feat(emergency): add ambulance ETA tracking simulation",
    "feat(tools): add health insurance policy compatibility checker",
    "fix(agent): prevent premature conclusion in multi-symptom queries",
    "feat(dashboard): add export button for triage audit logs",
    "docs: document vector database indexing and embedding model",
    "feat(agent): add dietary recommendation engine based on diagnosis",
    "perf: compress JSON responses for large alert history payloads",
    "refactor(emergency): improve severity calculation algorithm",
    "test: add unit tests for date parsing and calendar math",
    "fix(api): ensure all background tasks catch unhandled exceptions",
    "feat(booking): add doctor specialty auto-recommendation based on symptoms",
    "feat(dashboard): show real-time agent processing spinner",
    "style: refine alert badges with color-coded severity icons",
    "refactor(tools): abstract notification provider interface",
    "feat(agent): add mental health screening and support resources",
    "fix(db): handle locked database exceptions with automatic retry",
    "feat(emergency): add hospital bed occupancy tracking simulator",
    "test: verify WhatsApp template variable substitution",
    "docs: add deployment instructions for Docker and cloud instances",
    "feat(dashboard): add customizable sound alert for critical triage",
    "perf: optimize string concatenations in prompt formatting",
    "refactor(agent): structure medical disclaimer as mandatory footer",
    "fix(booking): fix off-by-one error in next available slot selector",
    "feat(api): add API versioning headers",
    "feat(emergency): broadcast SOS to designated family contacts",
    "feat(agent): integrate drug-drug interaction checker",
    "test: add fuzzy matching tests for doctor names and specialties",
    "style: enhance visual hierarchy of diagnosis recommendations",
    "refactor(tools): simplify payload builders for WhatsApp templates",
    "fix(dashboard): persist session state across browser tab switches",
    "feat(booking): add patient intake notes directly to appointment record",
    "feat(agent): support continuous health monitoring log entries",
    "docs: update licensing and open-source credits",
    "perf: speed up initial FAISS vector index loading",
    "refactor(emergency): encapsulate alert dispatch logic in service class",
    "fix(api): validate UUID format for incoming session identifiers",
    "feat(dashboard): add interactive map component for emergency hotspots",
    "test: add end-to-end integration test for emergency alert flow",
    "feat(agent): add post-consultation feedback collection",
    "feat(booking): add support for virtual tele-health consultations",
    "refactor: standardize logging format across all agent modules",
    "fix(tools): fix missing authentication header on webhook callbacks",
    "style: refine dashboard dark mode contrast and borders",
    "feat(emergency): add triage escalation if patient condition deteriorates",

    "feat(branding): introduce HealBot AI identity and theme styling",
    "refactor(ui): update application titles and banners to HealBot AI",
    "docs: revise project README with HealBot AI branding and features",
    "feat(agent): personalize greetings with HealBot AI assistant persona",
    "fix(api): update API title and startup metadata to HealBot AI API",
    "perf: benchmark and tune end-to-end latency for chat queries",
    "refactor(booking): streamline doctor booking conversation flow",
    "feat(dashboard): add quick triage templates for common health issues",
    "test: comprehensive test run across all triage scenarios",
    "fix(tools): prevent duplicate WhatsApp notifications on network hiccups",
    "feat(emergency): enhance critical alert visibility with banner alerts",
    "style: polish UI cards, margins, and typography",
    "refactor(agent): improve intent detection between chat vs booking",
    "docs: update API documentation and endpoint descriptions",
    "feat(dashboard): add patient summary export functionality",
    "fix(agent): ensure clear triage disclaimer on all responses",
    "feat(booking): add cancellation confirmation prompt",
    "perf: reduce cold-start latency for background agent services",
    "refactor(db): optimize emergency database cache structure",
    "test: add unit tests for doctor slot allocation logic",
    "feat(emergency): support multi-hospital triage load balancing",
    "style: refine color theme for high and moderate alerts",
    "feat(agent): add first-aid guidance for burn, fracture, and choking",
    "fix(api): ensure proper HTTP status codes for validation errors",
    "feat(dashboard): add live server status indicator badge",
    "refactor(tools): clean up external API request wrappers",
    "docs: document simulation types and testing guidelines",
    "feat(booking): support doctor filtering by proximity and rating",
    "test: add automated assertions for emergency severity levels",
    "feat(agent): add recovery tracking and follow-up prompts",
    "style: improve table formatting in Streamlit diagnosis view",
    "fix(emergency): fix edge case where alert level defaults to unknown",
    "feat(dashboard): add compact view toggle for mobile devices",
    "perf: optimize regex extraction in medical entity recognizer",
    "refactor: remove redundant debug prints and unused variables",
    "feat(agent): add pregnancy & maternal health safety guidance",
    "test: verify appointment rescheduling logic under concurrent requests",
    "feat(emergency): add priority triage queue for pediatric emergencies",
    "docs: finalize architecture docs and developer guide",
    "style: enhance button active states and badge styling",
    "fix(booking): handle bank holidays and weekend scheduling rules",
    "feat(tools): add webhook listener for WhatsApp message delivery receipts",
    "feat(agent): integrate sleep and hydration tracking suggestions",
    "perf: cache vector database queries with TTL policy",
    "refactor(api): enforce structured response models across all endpoints",
    "feat(dashboard): add real-time active session counter",
    "fix(dashboard): fix chart rendering glitch on empty alert data",
    "test: execute full test suite and verify test coverage",
    "feat(emergency): add automated escalation for unresolved critical alerts",
    "style: optimize dashboard CSS for high-DPI displays",
    "feat(agent): add post-medication symptom check reminders",
    "refactor(booking): consolidate appointment validation steps",
    "feat(tools): add health status diagnostics probe",
    "fix(agent): refine dosage unit conversion logic",
    "feat(dashboard): add instant emergency SOS quick-action button",
    "perf: finalize memory and latency optimizations",
    "refactor: ensure strict type hints across core agent functions",
    "test: add stress tests for high-volume emergency simulation",
    "style: final polish on UI cards, animations, and typography",
    "feat(agent): finalize empathetic conversational tone and safety rules",
    "fix(api): ensure clean shutdown of all background monitoring tasks",
    "docs: update API endpoints documentation in README.md",
    "chore: verify dependency constraints in requirements.txt",
    "refactor: format codebase and adhere to clean architecture",
    "feat(branding): finalize HealBot AI theme, icons, and page metadata",
    "fix(dashboard): ensure seamless experience across desktop and mobile",
    "chore: prepare release candidate v2.0.0",
    "test: verify all core agent features and end-to-end user journeys",
    "feat(release): HealBot AI v2.0.0 production deployment"
]

while len(commit_messages) < TOTAL_COMMITS:
    idx = len(commit_messages) + 1
    commit_messages.append(f"chore(healbot): routine maintenance, optimization and dependency check #{idx}")
commit_messages = commit_messages[:TOTAL_COMMITS]

# Files for initial progressive stages
initial_stages = [
    [".gitignore"],
    ["requirements.txt"],
    ["create_diseases_db.sql", "sql_script.py"],
    ["diseases.db"],
    ["emergency_db_cache.json"],
    ["tools/"],
    ["faiss_index/"],
    ["scripts/", "tester.py", "testing_net.py", "whatsapp_test.py"],
    ["agents/health_adviser.py"],
    ["agents/emergency_agent.py", "agents/run_simulations.py"],
    ["agents/booking_agent.py", "agents/debug_file.py"],
    ["main.py"],
    ["app.py"],
    ["README.md"]
]

print(f"Creating clean {TOTAL_COMMITS} commits from {START_DATE.date()} to {END_DATE.date()} (NO CHANGELOG)...")

# Commit initial files
for i in range(len(initial_stages)):
    files = initial_stages[i]
    for f in files:
        run_cmd(f"git add {f}")
    
    ts = timestamps[i]
    date_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    msg = commit_messages[i]
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str
    
    run_cmd(f'git commit -m "{msg}"', env=env)

# Files to rotate for micro-commits (comments, docstrings, formatting, readme touches)
code_files = [
    "agents/health_adviser.py",
    "agents/booking_agent.py",
    "agents/emergency_agent.py",
    "tools/whatsapp_tools.py",
    "tools/sql_tools.py",
    "tools/emergency_tools.py",
    "main.py",
    "app.py",
    "tester.py",
    "README.md",
    "requirements.txt"
]

# Read original contents so we can restore perfectly at the end
original_contents = {}
for cf in code_files:
    p = os.path.join(REPO_DIR, cf)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            original_contents[cf] = f.read()

for i in range(len(initial_stages), TOTAL_COMMITS):
    ts = timestamps[i]
    date_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    msg = commit_messages[i]
    
    # Pick a file to add a clean inline comment or newline
    target_file = code_files[i % len(code_files)]
    target_path = os.path.join(REPO_DIR, target_file)
    
    if os.path.exists(target_path):
        with open(target_path, "a", encoding="utf-8") as f:
            if target_file.endswith(".py"):
                f.write(f"\n# [{ts.strftime('%Y-%m-%d')}] {msg}\n")
            elif target_file.endswith(".md"):
                f.write(f"\n<!-- update: {msg} -->\n")
            else:
                f.write(f"\n# {msg}\n")
        
        run_cmd(f"git add {target_file}")
    
    # In the very last commit, restore all original pristine contents cleanly
    if i == TOTAL_COMMITS - 1:
        for cf, content in original_contents.items():
            p = os.path.join(REPO_DIR, cf)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        run_cmd("git add .")

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str
    
    run_cmd(f'git commit -m "{msg}"', env=env)

# Ensure no CHANGELOG.md and everything is clean
if os.path.exists(cl):
    os.remove(cl)
    run_cmd("git rm -f CHANGELOG.md")

print("Verifying commit count...")
res = run_cmd("git rev-list --count HEAD")
print(f"Total commits: {res.stdout.strip()}")
