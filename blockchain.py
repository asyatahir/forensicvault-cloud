
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# Blockchain configuration
RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise RuntimeError("Unable to connect to Sepolia.")

if w3.eth.chain_id != 11155111:
    raise RuntimeError("Incorrect blockchain network.")

account = w3.eth.account.from_key(PRIVATE_KEY)

# Smart contract ABI
CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "_hash", "type": "string"},
            {"name": "_caseID", "type": "string"}
        ],
        "name": "storeEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "index", "type": "uint256"}
        ],
        "name": "getEvidence",
        "outputs": [
            {"name": "", "type": "string"},
            {"name": "", "type": "string"},
            {"name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getCount",
        "outputs": [
            {"name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [
            {"name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=CONTRACT_ABI
)


# Register evidence on blockchain
def store_on_blockchain(evidence_hash, case_id):

    if contract.functions.owner().call().lower() != account.address.lower():
        raise RuntimeError("Unauthorized blockchain wallet.")

    if len(evidence_hash) != 64:
        raise ValueError("Invalid SHA-256 hash.")

    int(evidence_hash, 16)

    function = contract.functions.storeEvidence(
        evidence_hash.lower(), case_id
    )

    gas_estimate = function.estimate_gas({
        "from": account.address
    })

    transaction = function.build_transaction({
        "from": account.address,
        "chainId": 11155111,
        "nonce": w3.eth.get_transaction_count(
            account.address, "pending"
        ),
        "gas": int(gas_estimate * 1.2),
        "gasPrice": w3.eth.gas_price
    })

    signed_tx = account.sign_transaction(transaction)

    raw_tx = getattr(signed_tx, "raw_transaction", None)

    if raw_tx is None:
        raw_tx = signed_tx.rawTransaction

    tx_hash = w3.eth.send_raw_transaction(raw_tx)

    print("Transaction Hash:", w3.to_hex(tx_hash))

    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash, timeout=300
    )

    if receipt.status != 1:
        raise RuntimeError("Blockchain transaction failed.")

    return w3.to_hex(tx_hash)


# Retrieve all blockchain evidence records
def get_all_evidence():

    count = contract.functions.getCount().call()

    all_evidence = []

    for i in range(count):

        hash_val, case_id, timestamp = (
            contract.functions.getEvidence(i).call()
        )

        all_evidence.append({
            "index": i,
            "hash": hash_val,
            "case_id": case_id,
            "timestamp": timestamp
        })

    return all_evidence


# Verify evidence integrity
def verify_hash(input_hash):

    count = contract.functions.getCount().call()

    for i in range(count):

        stored_hash, case_id, timestamp = (
            contract.functions.getEvidence(i).call()
        )

        if stored_hash.lower() == input_hash.lower():
            return True, case_id

    return False, None
