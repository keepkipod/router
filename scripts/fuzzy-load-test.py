#!/usr/bin/env python3
"""
Fuzzy load test script for Cell Router API
Generates various types of traffic to populate monitoring dashboards
"""

import requests
import random
import time
import json
import threading
from datetime import datetime, timedelta
import signal
import sys

# Configuration
ROUTER_URL = "http://localhost:8080"  # Change if using different port
API_ENDPOINT = f"{ROUTER_URL}/api/route"
HEALTH_ENDPOINT = f"{ROUTER_URL}/health"
METRICS_ENDPOINT = f"{ROUTER_URL}/metrics"

# Test configuration
VALID_API_KEYS = ["demo-key-1", "demo-key-2", "test-key"]
INVALID_API_KEYS = ["wrong-key", "expired-key", "hack-attempt", ""]
VALID_CELL_IDS = ["1", "2", "3"]
INVALID_CELL_IDS = ["4", "99", "0", "-1", "abc", ""]

# Test duration
TEST_DURATION_MINUTES = 5
END_TIME = datetime.now() + timedelta(minutes=TEST_DURATION_MINUTES)

# Statistics
stats = {
    "total_requests": 0,
    "successful": 0,
    "auth_failures": 0,
    "validation_errors": 0,
    "server_errors": 0,
    "timeouts": 0
}

# Thread-safe lock for stats
stats_lock = threading.Lock()

# Flag to stop threads
stop_threads = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global stop_threads
    print("\n\nStopping test gracefully...")
    stop_threads = True
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def update_stats(key):
    """Thread-safe stats update"""
    with stats_lock:
        stats[key] += 1
        stats["total_requests"] += 1


def send_request(cell_id, api_key=None, timeout=5):
    """Send a single request to the router"""
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["X-API-Key"] = api_key
    
    payload = {"cellID": cell_id}
    
    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            update_stats("successful")
            return "success", response.status_code
        elif response.status_code == 401:
            update_stats("auth_failures")
            return "auth_failed", response.status_code
        elif response.status_code == 403:
            update_stats("auth_failures")
            return "forbidden", response.status_code
        elif response.status_code == 422:
            update_stats("validation_errors")
            return "validation_error", response.status_code
        elif response.status_code >= 500:
            update_stats("server_errors")
            return "server_error", response.status_code
        else:
            return "other", response.status_code
            
    except requests.exceptions.Timeout:
        update_stats("timeouts")
        return "timeout", 0
    except Exception as e:
        return "error", 0


def normal_traffic_pattern():
    """Simulate normal traffic with valid requests"""
    while datetime.now() < END_TIME and not stop_threads:
        cell_id = random.choice(VALID_CELL_IDS)
        api_key = random.choice(VALID_API_KEYS)
        
        send_request(cell_id, api_key)
        
        # Normal rate: 1-5 requests per second
        time.sleep(random.uniform(0.2, 1.0))


def burst_traffic_pattern():
    """Simulate burst traffic"""
    while datetime.now() < END_TIME and not stop_threads:
        # Burst for 10-30 seconds
        burst_duration = random.uniform(10, 30)
        burst_end = datetime.now() + timedelta(seconds=burst_duration)
        
        print(f"\n🚀 Starting burst traffic for {burst_duration:.0f} seconds...")
        
        while datetime.now() < burst_end and not stop_threads:
            # 80% valid requests during burst
            if random.random() < 0.8:
                cell_id = random.choice(VALID_CELL_IDS)
                api_key = random.choice(VALID_API_KEYS)
            else:
                cell_id = random.choice(VALID_CELL_IDS + INVALID_CELL_IDS)
                api_key = random.choice(VALID_API_KEYS + INVALID_API_KEYS)
            
            send_request(cell_id, api_key, timeout=2)
            
            # High rate: 10-50 requests per second
            time.sleep(random.uniform(0.02, 0.1))
        
        # Cool down period
        cooldown = random.uniform(20, 40)
        print(f"💤 Cooling down for {cooldown:.0f} seconds...")
        time.sleep(cooldown)


def invalid_requests_pattern():
    """Simulate various invalid requests"""
    while datetime.now() < END_TIME and not stop_threads:
        request_type = random.choice([
            "invalid_cell",
            "invalid_api_key",
            "missing_api_key",
            "both_invalid",
            "malformed"
        ])
        
        if request_type == "invalid_cell":
            cell_id = random.choice(INVALID_CELL_IDS)
            api_key = random.choice(VALID_API_KEYS)
        elif request_type == "invalid_api_key":
            cell_id = random.choice(VALID_CELL_IDS)
            api_key = random.choice(INVALID_API_KEYS)
        elif request_type == "missing_api_key":
            cell_id = random.choice(VALID_CELL_IDS)
            api_key = None
        elif request_type == "both_invalid":
            cell_id = random.choice(INVALID_CELL_IDS)
            api_key = random.choice(INVALID_API_KEYS)
        else:  # malformed
            cell_id = ""
            api_key = ""
        
        send_request(cell_id, api_key)
        
        # Moderate rate for invalid requests
        time.sleep(random.uniform(0.5, 2.0))


def slow_requests_pattern():
    """Simulate slow requests that might timeout"""
    while datetime.now() < END_TIME and not stop_threads:
        cell_id = random.choice(VALID_CELL_IDS)
        api_key = random.choice(VALID_API_KEYS)
        
        # Use very short timeout to simulate timeouts
        send_request(cell_id, api_key, timeout=0.1)
        
        # Slow rate
        time.sleep(random.uniform(5, 10))


def targeted_cell_pattern():
    """Target specific cells to show distribution"""
    while datetime.now() < END_TIME and not stop_threads:
        # 60% to cell 1, 30% to cell 2, 10% to cell 3
        rand = random.random()
        if rand < 0.6:
            cell_id = "1"
        elif rand < 0.9:
            cell_id = "2"
        else:
            cell_id = "3"
        
        api_key = random.choice(VALID_API_KEYS)
        send_request(cell_id, api_key)
        
        time.sleep(random.uniform(0.3, 0.7))


def health_check_pattern():
    """Periodic health checks"""
    while datetime.now() < END_TIME and not stop_threads:
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=5)
            if response.status_code == 200:
                print("✅ Health check: OK")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Check every 30 seconds
        time.sleep(30)


def print_stats():
    """Print statistics periodically"""
    while datetime.now() < END_TIME and not stop_threads:
        time.sleep(10)
        with stats_lock:
            total = stats["total_requests"]
            if total > 0:
                success_rate = (stats["successful"] / total) * 100
                error_rate = ((stats["server_errors"] + stats["timeouts"]) / total) * 100
                
                print(f"\n📊 Stats Update:")
                print(f"  Total Requests: {total}")
                print(f"  Success Rate: {success_rate:.1f}%")
                print(f"  Error Rate: {error_rate:.1f}%")
                print(f"  Auth Failures: {stats['auth_failures']}")
                print(f"  Validation Errors: {stats['validation_errors']}")
                print(f"  Timeouts: {stats['timeouts']}")
                print(f"  Time Remaining: {(END_TIME - datetime.now()).seconds}s")


def main():
    """Main function to run the fuzzy test"""
    print(f"""
🧪 Cell Router Fuzzy Load Test
================================
Duration: {TEST_DURATION_MINUTES} minutes
Target: {ROUTER_URL}
Press Ctrl+C to stop early
================================
    """)
    
    # Create threads for different traffic patterns
    threads = [
        threading.Thread(target=normal_traffic_pattern, name="Normal"),
        threading.Thread(target=burst_traffic_pattern, name="Burst"),
        threading.Thread(target=invalid_requests_pattern, name="Invalid"),
        threading.Thread(target=slow_requests_pattern, name="Slow"),
        threading.Thread(target=targeted_cell_pattern, name="Targeted"),
        threading.Thread(target=health_check_pattern, name="Health"),
        threading.Thread(target=print_stats, name="Stats")
    ]
    
    # Start all threads
    for thread in threads:
        thread.daemon = True
        thread.start()
        print(f"✅ Started {thread.name} traffic pattern")
    
    # Wait for test duration or interruption
    try:
        while datetime.now() < END_TIME and not stop_threads:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    # Final statistics
    print("\n\n" + "="*50)
    print("🏁 FINAL TEST RESULTS")
    print("="*50)
    
    with stats_lock:
        total = stats["total_requests"]
        if total > 0:
            print(f"Total Requests: {total}")
            print(f"Successful: {stats['successful']} ({stats['successful']/total*100:.1f}%)")
            print(f"Auth Failures: {stats['auth_failures']} ({stats['auth_failures']/total*100:.1f}%)")
            print(f"Validation Errors: {stats['validation_errors']} ({stats['validation_errors']/total*100:.1f}%)")
            print(f"Server Errors: {stats['server_errors']} ({stats['server_errors']/total*100:.1f}%)")
            print(f"Timeouts: {stats['timeouts']} ({stats['timeouts']/total*100:.1f}%)")
            
            # Calculate requests per second
            duration_seconds = TEST_DURATION_MINUTES * 60
            rps = total / duration_seconds
            print(f"\nAverage RPS: {rps:.2f}")
        else:
            print("No requests were sent. Check if the router is running.")
    
    print("\n✅ Test completed! Check your Grafana dashboards.")
    print(f"   http://localhost:3000")


if __name__ == "__main__":
    main()