
import os
from dotenv import load_dotenv
from solcx import compile_source, install_solc
from web3 import Web3

load_dotenv()

# Connect to Ethereum Sepolia
rpc_url = os.getenv("SEPOLIA_RPC_URL")
private_key = os.getenv("WALLET_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(rpc_url))

if not w3.is_connected():
    raise RuntimeError("Blockchain connection failed.")

if w3.eth.chain_id != 11155111:
    raise RuntimeError("Wrong network. Expected Sepolia.")

account = w3.eth.account.from_key(private_key)

print("Connected to Ethereum Sepolia")
print("Wallet balance:", w3.from_wei(
    w3.eth.get_balance(account.address), "ether"
), "ETH")

# Compile smart contract
print("Compiling smart contract...")

install_solc("0.8.0")

with open("contract.sol", "r") as f:
    contract_source = f.read()

compiled = compile_source(
    contract_source,
    solc_version="0.8.0"
)

contract_interface = compiled["<stdin>:EvidenceStorage"]

EvidenceStorage = w3.eth.contract(
    abi=contract_interface["abi"],
    bytecode=contract_interface["bin"]
)

# Estimate deployment cost
gas_estimate = EvidenceStorage.constructor().estimate_gas({
    "from": account.address
})

gas_price = w3.eth.gas_price
gas_limit = int(gas_estimate * 1.2)
estimated_cost = gas_limit * gas_price

print("Estimated maximum deployment cost:",
      w3.from_wei(estimated_cost, "ether"), "ETH")

if w3.eth.get_balance(account.address) < estimated_cost:
    raise RuntimeError("Insufficient Sepolia test ETH.")

confirm = input("Deploy to Sepolia? (yes/no): ")

if confirm.strip().lower() != "yes":
    print("Deployment cancelled.")
    raise SystemExit

# Build transaction
transaction = EvidenceStorage.constructor().build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(
        account.address, "pending"
    ),
    "chainId": 11155111,
    "gas": gas_limit,
    "gasPrice": gas_price
})

# Sign transaction securely
signed_tx = account.sign_transaction(transaction)

raw_tx = getattr(signed_tx, "raw_transaction", None)

if raw_tx is None:
    raw_tx = signed_tx.rawTransaction

# Send transaction
tx_hash = w3.eth.send_raw_transaction(raw_tx)

print("Transaction submitted!")
print("Transaction Hash:", w3.to_hex(tx_hash))
print("Waiting for blockchain confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(
    tx_hash, timeout=300
)

if receipt.status != 1:
    raise RuntimeError("Contract deployment failed.")

print("Contract deployed successfully!")
print("Contract Address:", receipt.contractAddress)
print("Block Number:", receipt.blockNumber)
print("Gas Used:", receipt.gasUsed)

print("View on Etherscan:")
print(f"https://sepolia.etherscan.io/address/{receipt.contractAddress}")
