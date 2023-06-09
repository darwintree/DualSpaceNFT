from conflux_web3 import Web3 as CWeb3 # do hook
from cfx_utils.types import ChecksumAddress
from cfx_account import Account as CfxAccount
from cfx_account import LocalAccount as CfxLocalAccount
from cfx_address import Base32Address
from conflux_web3.contract import ConfluxContract

import os, pytest, json
from typing import cast, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

from eth_account import Account
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from web3.contract.contract import Contract
from web3 import Web3, HTTPProvider


load_dotenv()

@pytest.fixture(scope="session")
def deployed() -> bool:
    return bool(os.environ.get("deployed", False))

@pytest.fixture(scope="session")
def private_key() -> str:
    return os.environ["PRIVATE_KEY"]

@pytest.fixture(scope="session")
def e_w3(private_key: str) -> Web3:
    w3 = Web3(HTTPProvider("https://evmtestnet.confluxrpc.com/"))
    acct = Account.from_key(private_key)
    w3.middleware_onion.add(
        construct_sign_and_send_raw_middleware(acct)
    )
    w3.eth.default_account = acct.address
    return w3


@pytest.fixture(scope="session")
def c_w3(private_key: str) -> CWeb3:
    w3 = CWeb3(HTTPProvider("https://test.confluxrpc.com"))
    w3.cfx.default_account = w3.account.from_key(private_key)
    return w3


# returns (abi, bytecode)
def get_metadata(p: str) -> Tuple[str, str]:
    with open(p) as f:
        metadata = json.load(f)
        return metadata["abi"], metadata["bytecode"]

@pytest.fixture(scope="session")
def core_contract(deployed: bool, c_w3: CWeb3) -> ConfluxContract:
    abi, bytecode = get_metadata("build/contracts/DualSpaceNFTCore.json")
    if deployed:
        address = cast(Base32Address, os.environ["CORE_CONTRACT_ADDRESS"])
    else:
        construct_c = c_w3.cfx.contract(bytecode=bytecode, abi=abi)
        constructor = construct_c.constructor(
            os.environ["NAME"],
            os.environ["SYMBOL"],
            c_w3.cfx.contract(name="CrossSpaceCall").address
        )
        deploy_hash = constructor.transact()
        receipt = c_w3.cfx.wait_for_transaction_receipt(deploy_hash)
        address = receipt["contractCreated"]
        if address == None:
            raise Exception

    return c_w3.cfx.contract(address=address, abi=abi)


@pytest.fixture(scope="session")
def evm_contract(deployed: bool, e_w3: Web3, core_contract: ConfluxContract) -> Contract:
    abi, bytecode = get_metadata("build/contracts/DualSpaceNFTEVM.json")
    if deployed:
        address = cast(ChecksumAddress, os.environ["EVM_CONTRACT_ADDRESS"])
    else:
        construct_c = e_w3.eth.contract(bytecode=bytecode, abi=abi)
        mappingAddress = core_contract.address.mapped_evm_space_address
        deploy_hash = construct_c.constructor(
            os.environ["NAME"],
            os.environ["SYMBOL"],
            bytes.fromhex(mappingAddress[2:])
        ).transact({
            "gasPrice": 20 * 10**9
        })
        receipt = e_w3.eth.wait_for_transaction_receipt(deploy_hash)
        address = receipt["contractAddress"]
        if address == None:
            raise Exception

        # bind core to espace
        core_contract.functions.setEvmContractAddress(bytes.fromhex(address[2:])).transact().executed()

    return e_w3.eth.contract(address=address, abi=abi)

@dataclass
class BatchSetting:
    batch_nbr: int
    signer: CfxLocalAccount

@pytest.fixture(scope="session")
def batch_setting(
    c_w3: CWeb3, core_contract: ConfluxContract, evm_contract: ConfluxContract, cw3_accounts: Tuple[CfxLocalAccount, CfxLocalAccount, CfxLocalAccount]
) -> BatchSetting:
    raw = int(os.environ["BATCH_NBR"])
    signer = cw3_accounts[1]
    core_contract.functions.startBatch(
        raw, signer.address, 1
    ).transact().executed()
    return BatchSetting(raw, signer)


@pytest.fixture(scope="session")
def cw3_accounts(c_w3: CWeb3) -> Tuple[CfxLocalAccount, CfxLocalAccount, CfxLocalAccount]:
    '''
    returns util accounts [user_account, oracle_signer_account, random_account]
    '''
    faucet = c_w3.cfx.contract(name="Faucet")
    user_account = c_w3.account.create()
    oracle_signer = c_w3.account.create()
    random_account = c_w3.account.create()
    c_w3.wallet.add_accounts([
        user_account, oracle_signer, random_account
    ])
    faucet.functions.claimCfx().transact({
        "from": user_account.address
    })
    faucet.functions.claimCfx().transact({
        "from": oracle_signer.address
    })
    faucet.functions.claimCfx().transact({
        "from": random_account.address
    }).executed()
    return user_account, oracle_signer, random_account
    

@pytest.fixture(scope="session")
def user_private_key(cw3_accounts: Tuple[CfxLocalAccount, CfxLocalAccount, CfxLocalAccount]) -> bytes:
    return cw3_accounts[0].key

@pytest.fixture(scope="session")
def random_core_sender(cw3_accounts: Tuple[CfxLocalAccount, CfxLocalAccount, CfxLocalAccount]) -> CfxLocalAccount:
    return cw3_accounts[2]
