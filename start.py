import os
import sys
import time
import subprocess
import threading
import webbrowser
import urllib.request
import json
import shutil

# Set UTF-8 encoding for standard streams on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    print(f"""
{CYAN}{BOLD}===================================================================
   AI DOCUMENT INTELLIGENCE SYSTEM LAUNCHER
   Stack: Next.js + FastAPI + Docling + Local Qwen 2.5 (GTX 1650)
==================================================================={RESET}
""")

def free_ports():
    """Ensure ports 8000 and 3000 are clear before starting."""
    if sys.platform == "win32":
        cmd = "Get-Process -Id (Get-NetTCPConnection -LocalPort 8000, 3000 -State Listen -ErrorAction SilentlyContinue).OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
        try:
            subprocess.run(["powershell", "-Command", cmd], capture_output=True)
        except Exception:
            pass

def check_ollama():
    print(f"[*] Checking Localhost Ollama (Qwen 2.5)...", end=" ", flush=True)
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                print(f"{GREEN}ONLINE{RESET}")
                if any("qwen2.5" in m for m in models):
                    print(f"    {GREEN}[OK] Found Qwen model in Ollama: {[m for m in models if 'qwen' in m]}{RESET}")
                else:
                    print(f"    {YELLOW}[!] Notice: 'qwen2.5:3b' not seen in tags. Run `ollama run qwen2.5:3b` if needed.{RESET}")
                return True
    except Exception:
        print(f"{YELLOW}OFFLINE / UNREACHABLE{RESET}")
        print(f"    {YELLOW}[!] Please make sure Ollama is running (`ollama serve` or open Ollama app){RESET}")
        return False

def check_docker():
    print(f"[*] Checking Database engine...", end=" ", flush=True)
    try:
        res = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{GREEN}PostgreSQL & pgvector active via Docker{RESET}")
            return True
    except Exception:
        pass
    print(f"{GREEN}Local SQLite Database active (doc_intelligence.db){RESET}")
    return False

def get_backend_python():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    venv_dir = os.path.join(backend_dir, ".venv")
    
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")

    if os.path.exists(venv_python):
        return venv_python

    print(f"[*] Creating backend virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    
    print(f"[*] Installing requirements in virtual environment...")
    req_file = os.path.join(backend_dir, "requirements.txt")
    subprocess.run([venv_pip, "install", "-r", req_file], check=True)
    return venv_python

def stream_process_output(pipe, prefix, color):
    try:
        for line in iter(pipe.readline, ''):
            if line:
                print(f"{color}[{prefix}]{RESET} {line.rstrip()}", flush=True)
    except Exception:
        pass

def main():
    print_banner()
    free_ports()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    venv_dir = os.path.join(backend_dir, ".venv")

    # 1. Verify services
    check_ollama()
    check_docker()
    backend_python = get_backend_python()
    print(f"[*] Backend Python: {CYAN}{backend_python}{RESET}")

    # 2. Check frontend dependencies
    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print(f"[*] Installing frontend dependencies (`npm install`)...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        subprocess.run([npm_cmd, "install"], cwd=frontend_dir, shell=True)

    print(f"\n{GREEN}{BOLD}[+] Launching Services...{RESET}")
    print(f"    - Backend API:  {CYAN}http://localhost:8000{RESET} (Docs: {CYAN}http://localhost:8000/docs{RESET})")
    print(f"    - Frontend UI:  {CYAN}http://localhost:3000{RESET}")
    print(f"    - Press {RED}{BOLD}Ctrl + C{RESET} at any time to stop all services.\n")

    processes = []
    
    try:
        # Build environment for Backend subprocess
        backend_env = os.environ.copy()
        backend_env["PYTHONPATH"] = backend_dir
        if sys.platform == "win32":
            backend_env["PATH"] = os.path.join(venv_dir, "Scripts") + os.pathsep + backend_env.get("PATH", "")
        else:
            backend_env["PATH"] = os.path.join(venv_dir, "bin") + os.pathsep + backend_env.get("PATH", "")

        # Launch Backend
        backend_cmd = [backend_python, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=backend_env
        )
        processes.append(backend_proc)
        
        t1 = threading.Thread(target=stream_process_output, args=(backend_proc.stdout, "BACKEND", CYAN), daemon=True)
        t1.start()

        # Launch Frontend
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=True
        )
        processes.append(frontend_proc)
        
        t2 = threading.Thread(target=stream_process_output, args=(frontend_proc.stdout, "FRONTEND", GREEN), daemon=True)
        t2.start()

        # Auto open browser
        def open_browser():
            time.sleep(3)
            webbrowser.open("http://localhost:3000")

        threading.Thread(target=open_browser, daemon=True).start()

        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Stopping all services...{RESET}")
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        print(f"{GREEN}[OK] Shutdown complete. Goodbye!{RESET}\n")

if __name__ == "__main__":
    main()
