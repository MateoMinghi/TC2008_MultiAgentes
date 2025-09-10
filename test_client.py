#!/usr/bin/env python3
"""
Test client for the Tactical Rescue Simulation Server.
Sends a request to the /run_simulation endpoint and saves the response to a JSON file.
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

def test_simulation_endpoint(server_url="http://localhost:5000", output_file="simulation_output.json"):
    """
    Test the simulation endpoint and save the response to a JSON file.
    
    Args:
        server_url (str): The base URL of the simulation server
        output_file (str): Path where to save the simulation output
    """
    endpoint = f"{server_url}/run_simulation"
    
    print("=" * 60)
    print("Tactical Rescue Simulation - Test Client")
    print("=" * 60)
    print(f"Server URL: {server_url}")
    print(f"Endpoint: {endpoint}")
    print(f"Output file: {output_file}")
    print("-" * 60)
    
    try:
        # Check if server is healthy first
        print("🔍 Checking server health...")
        health_response = requests.get(f"{server_url}/health", timeout=10)
        
        if health_response.status_code == 200:
            print("✅ Server is healthy")
            health_data = health_response.json()
            print(f"   Status: {health_data.get('status', 'unknown')}")
        else:
            print(f"⚠️  Server health check failed: {health_response.status_code}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Make sure the server is running with: python server.py")
        return False
    
    try:
        print("\n🚀 Starting simulation...")
        start_time = time.time()
        
        # Send request to run simulation
        response = requests.get(endpoint, timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Simulation completed in {duration:.2f} seconds")
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Parse the JSON response
            simulation_data = response.json()
            
            # Add metadata about the test run
            test_metadata = {
                "test_run_timestamp": datetime.now().isoformat(),
                "server_url": server_url,
                "duration_seconds": round(duration, 2),
                "response_status": response.status_code
            }
            
            # Add test metadata to the simulation data
            if "meta" not in simulation_data:
                simulation_data["meta"] = {}
            simulation_data["meta"]["test_info"] = test_metadata
            
            # Save to file
            output_path = Path(output_file)
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(simulation_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Simulation data saved to: {output_path.absolute()}")
            
            # Display summary
            print("\n📈 Simulation Summary:")
            print(f"   Result: {simulation_data.get('result', 'unknown')}")
            print(f"   Rescued: {simulation_data.get('rescued', 0)}")
            print(f"   Lost: {simulation_data.get('lost', 0)}")
            print(f"   Damage: {simulation_data.get('damage', 0)}")
            
            if "meta" in simulation_data:
                meta = simulation_data["meta"]
                print(f"   Total steps: {meta.get('total_steps', 'unknown')}")
                print(f"   Initial hostages: {meta.get('initial_hostages', 'unknown')}")
                print(f"   False alarms investigated: {meta.get('false_alarms_investigated', 0)}")
            
            if "steps" in simulation_data:
                print(f"   Total events: {len(simulation_data['steps'])}")
            
            if "snapshots" in simulation_data:
                print(f"   Total snapshots: {len(simulation_data['snapshots'])}")
            
            return True
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                print(f"   Message: {error_data.get('message', 'No message')}")
            except:
                print(f"   Response text: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (simulation took too long)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function to run the test"""
    # You can modify these parameters as needed
    SERVER_URL = "http://localhost:5000"
    OUTPUT_FILE = "simulation_output.json"
    
    success = test_simulation_endpoint(SERVER_URL, OUTPUT_FILE)
    
    if success:
        print("\n✅ Test completed successfully!")
        print(f"📁 Check the file '{OUTPUT_FILE}' for the simulation results.")
    else:
        print("\n❌ Test failed!")
        print("   Make sure the server is running and try again.")

if __name__ == "__main__":
    main()