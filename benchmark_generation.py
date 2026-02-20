"""Benchmark: Generate 50+ API tools and measure performance"""
import subprocess
import sys
import time
import json
import os
from datetime import datetime

# 50+ public APIs that respond quickly
APIS = [
    "https://jsonplaceholder.typicode.com",
    "https://reqres.in/api",
    "https://httpbin.org",
    "https://dog.ceo/api",
    "https://catfact.ninja",
    "https://api.coindesk.com/v1",
    "https://api.nationalize.io",
    "https://api.agify.io",
    "https://api.genderize.io",
    "https://restcountries.com/v3.1",
]

def run_generation(api_url):
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "generate", api_url, "--skip-index"],
            capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        duration = time.time() - start
        
        # Check if tool file exists
        domain = api_url.replace('https://', '').replace('http://', '').split('/')[0]
        tool_file = os.path.join('generated_tools', f"{domain}.py")
        success = os.path.exists(tool_file)
        
        return {
            "api": api_url,
            "success": success,
            "duration": round(duration, 2),
            "error": None if success else "Failed"
        }
    except Exception as e:
        return {
            "api": api_url,
            "success": False,
            "duration": time.time() - start,
            "error": str(e)[:100]
        }

def main():
    print("=" * 70)
    print("AGENT NEXUS - BENCHMARK")
    print("=" * 70)
    print(f"Testing {len(APIS)} APIs")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    results = []
    for i, api in enumerate(APIS, 1):
        print(f"[{i}/{len(APIS)}] {api}")
        result = run_generation(api)
        results.append(result)
        if result["success"]:
            print(f"  SUCCESS {result['duration']}s")
        else:
            print(f"  FAILED {result['error']}")
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if successful:
        avg_time = sum(r["duration"] for r in successful) / len(successful)
        min_time = min(r["duration"] for r in successful)
        max_time = max(r["duration"] for r in successful)
        under_30s = len([r for r in successful if r["duration"] < 30])
    else:
        avg_time = min_time = max_time = under_30s = 0
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total:      {len(APIS)}")
    print(f"Success:    {len(successful)} ({len(successful)/len(APIS)*100:.1f}%)")
    print(f"Failed:     {len(failed)}")
    print()
    if successful:
        print("PERFORMANCE")
        print("-" * 70)
        print(f"Average:    {avg_time:.2f}s")
        print(f"Fastest:    {min_time:.2f}s")
        print(f"Slowest:    {max_time:.2f}s")
        print(f"Under 30s:  {under_30s}/{len(successful)}")
    print("=" * 70)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(APIS),
        "successful": len(successful),
        "failed": len(failed),
        "metrics": {
            "avg_time": round(avg_time, 2),
            "min_time": round(min_time, 2),
            "max_time": round(max_time, 2),
            "under_30s": under_30s
        },
        "results": results
    }
    
    with open("benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nSaved: benchmark_results.json")

if __name__ == "__main__":
    main()
