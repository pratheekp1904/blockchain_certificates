import os
import json
from solcx import install_solc, compile_source
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

SOLC_VERSION = os.getenv("SOLC_VERSION", "0.8.21")
install_solc(SOLC_VERSION)  # downloads compiler if needed

RPC = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")  # optional; if absent, expects unlocked accounts (Ganache)

w3 = Web3(Web3.HTTPProvider(RPC))
assert w3.is_connected(), f"Cannot connect to RPC at {RPC}"

# Read contract
with open("contracts/Certificate.sol", "r") as f:
    source = f.read()

compiled = compile_source(source, output_values=["abi", "bin"], solc_version=SOLC_VERSION)
_, contract_interface = compiled.popitem()
abi = contract_interface["abi"]
bytecode = contract_interface["bin"]

# Build contract object
Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

print("Deploying contract...")

if PRIVATE_KEY:
    account = w3.eth.account.from_key(PRIVATE_KEY)
    deployer = account.address
    nonce = w3.eth.get_transaction_count(deployer)
    tx = Contract.constructor().build_transaction({
        "from": deployer,
        "nonce": nonce,
        "gas": 4_000_000,
        "gasPrice": w3.to_wei("20", "gwei"),
        "chainId": w3.eth.chain_id
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
else:
    # Use unlocked account from node (Ganache provides unlocked accounts)
    deployer = w3.eth.accounts[0]
    tx_hash = Contract.constructor().transact({"from": deployer})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

address = receipt.contractAddress
print("Contract deployed at:", address)
# Save ABI+address to file for Flask
with open("contract_abi.json", "w") as f:
    json.dump({"abi": abi, "address": address}, f, indent=2)

print("ABI and address saved to contract_abi.json")
