import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Etherscan API key (sign up at https://etherscan.io/apis)
load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASE_URL = 'https://api.etherscan.io/api'

# Function to fetch newly deployed contracts
def fetch_new_contracts(start_block=0, end_block='latest'):
    url = f"{BASE_URL}?module=logs&action=getLogs&fromBlock={start_block}&toBlock={end_block}&address=0x0000000000000000000000000000000000000000&apikey={ETHERSCAN_API_KEY}"
    response = requests.get(url)
    return response.json()

# Function to fetch contract details (e.g., transactions and function calls)
def fetch_contract_details(contract_address):
    url = f"{BASE_URL}?module=contract&action=getabi&address={contract_address}&apikey={ETHERSCAN_API_KEY}"
    response = requests.get(url)
    return response.json()

# Function to format data for Logstash or Elasticsearch
def format_for_logstash(contract_data, contract_details):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "contract_address": contract_data.get("contractAddress"),
        "creator_address": contract_data.get("creatorAddress"),
        "abi": contract_details.get("result"),
        "function_calls": contract_data.get("functionCalls"),  # You can customize this further
        "risk_score": "low",  # Implement logic for risk scoring
    }
    return json.dumps(log_entry)

# Function to send data to Logstash (for local testing)
def send_to_logstash(data):
    # Example of sending data to Logstash via HTTP
    logstash_url = 'http://localhost:5044'  # Replace with your Logstash URL
    headers = {'Content-Type': 'application/json'}
    response = requests.post(logstash_url, data=data, headers=headers)
    return response.status_code

# Main function to orchestrate data fetching and processing
def main():
    # Fetch newly deployed contracts (example block range)
    contracts_data = fetch_new_contracts(start_block=12000000, end_block='latest')
    
    for contract in contracts_data['result']:
        print "CONTRACT= ", contract
        #contract_address = contract['address']
        
        # Fetch additional contract details (e.g., ABI, function calls)
        contract_details = fetch_contract_details(contract_address)
        
        # Format the data for Logstash
        logstash_data = format_for_logstash(contract, contract_details)
        
        # Send to Logstash for indexing into ElasticSearch
        status_code = send_to_logstash(logstash_data)
        
        if status_code == 200:
            print(f"Data sent successfully for contract: {contract_address}")
        else:
            print(f"Error sending data for contract: {contract_address} - Status Code: {status_code}")

if __name__ == "__main__":
    main()
