import requests
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Etherscan API key (sign up at https://etherscan.io/apis)
load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASE_URL = 'https://api.etherscan.io/v2/api?chainid=1'

FACTORY_ADDRESS = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"  # Uniswap V2 Factory

# Function to fetch newly deployed contracts
def fetch_new_contracts(start_block=0, end_block='latest'):
    print("Fetching new contracts...")
    url = f"{BASE_URL}&module=logs&action=getLogs&fromBlock={start_block}&toBlock={end_block}&address={FACTORY_ADDRESS}&apikey={ETHERSCAN_API_KEY}"
    #print("URL is ",url)
    response = requests.get(url)
    return response.json()

# Function to fetch contract details (e.g., transactions and function calls)
def fetch_contract_details(contract_address):
    url = f"{BASE_URL}&module=contract&action=getabi&address={contract_address}&apikey={ETHERSCAN_API_KEY}"
    response = requests.get(url)
    return response.json()

# Function to format data for Logstash or Elasticsearch
def format_for_logstash(contract_data, contract_details):
    #Get risk score & reason before building log event payload
    [risk_score, risk_reason] = assess_risk(contract_data, contract_details)

    #build log event payload
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "contract_address": contract_data.get("contractAddress"),
        "creator_address": contract_data.get("creatorAddress"),
        "abi": contract_details.get("result"),
        "function_calls": contract_data.get("functionCalls"),  # You can customize this further
        #"risk_score": assess_risk(contract_data, contract_details),
        "risk_score": risk_score,
        "risk_reason": risk_reason,
    }
    print("LOG ENTRY:")
    print(json.dumps(log_entry))
    return json.dumps(log_entry)

# Function to send data to Logstash (for local testing)
def send_to_logstash(data):
    # Example of sending data to Logstash via HTTP
    logstash_url = 'http://localhost:5044'  # Replace with your Logstash URL
    headers = {'Content-Type': 'application/json'}
    response = requests.post(logstash_url, data=data, headers=headers)
    return response.status_code

# Function to assess risk of returnd contract based on its ABI, creator history, and other factors. Returns 'high', 'medium', or 'low'.
def assess_risk(contract_data, contract_details):
    high_risk_patterns = [r"selfdestruct", r"delegatecall", r"callcode"]
    medium_risk_patterns = [r"call\(", r"approve\(.*, uint256\(.*-1\)\)", r"transferFrom"]
    
    # Default risk score
    risk_score = "low"
    
    # Extract relevant data
    abi = contract_details.get("result", "")
    creator_address = contract_data.get("creatorAddress", "")
    contract_address = contract_data.get("contractAddress", "")

    # 1 ABI Analysis
    if abi:
        for pattern in high_risk_patterns:
            if re.search(pattern, abi, re.IGNORECASE):
                #return "high"
                risk_score = "High"
                risk_reason = "Selfdestruct, delegeatecall or callcode found in ABI"
                return [risk_score, risk_reason]

        for pattern in medium_risk_patterns:
            if re.search(pattern, abi, re.IGNORECASE):
                risk_score = "medium"
                risk_reason = "Call, Approve, or transferFrom found in ABI"

    # 2 Creator Address Analysis (simplified example)
    known_scam_addresses = {"0xScamWallet1", "0xScamWallet2"}  # Replace with actual sources
    if creator_address in known_scam_addresses:
        #return "high"
        risk_score = "High"
        risk_reason = "Known scam address found"
        return [risk_score, risk_reason]

    # 3 Unverified Source Code
    if not contract_details.get("sourceCode"):
        #risk_score = "medium" if risk_score == "low" else "high"
        #risk_reason = "Source code not verified"
        
        # Risk assessment based on contract age and transactions
        contract_age_days = (current_time - contract_creation_date).days
        if contract_age_days < 30:  # Newly deployed contracts without code
            risk_score = "high"
            risk_reason = "Contract less than 30 days old"
        elif transaction_count < 10:  # Low interactions
            risk_score = "medium"
            risk_reason = "Low contract interaction"
        else:  # Older contracts without code
            risk_score = "low"
            risk_reason = "Contract greater than 30 days old and proven usage history"
        

    # 4 Placeholder for transaction analysis (can be expanded later)
    # e.g., checking large mints, low liquidity, mixer usage, etc.

    return [risk_score, risk_reason]


# Main function to orchestrate data fetching and processing
def main():
    print("Running main()")
    # Fetch newly deployed contracts (example block range)
    contracts_data = fetch_new_contracts(start_block=12000000, end_block='latest')

    #print(contracts_data)
    
    for contract in contracts_data['result']:
        contract_address = contract['address']
        
        # Fetch additional contract details (e.g., ABI, function calls)
        contract_details = fetch_contract_details(contract_address)
        #print("CONTRACT DETAILS: ", contract_details)
        
        # Format the data for Logstash
        logstash_data = format_for_logstash(contract, contract_details)
        
        # Send to Logstash for indexing into ElasticSearch
        #status_code = send_to_logstash(logstash_data)
        
        #if status_code == 200:
        #    print(f"Data sent successfully for contract: {contract_address}")
        #else:
        #    print(f"Error sending data for contract: {contract_address} - Status Code: {status_code}")

if __name__ == "__main__":
    main()
