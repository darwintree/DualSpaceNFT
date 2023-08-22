from conflux_web3 import Web3 as ConfluxWeb3
from web3 import Web3
from web3.middleware.signing import construct_sign_and_send_raw_middleware

import os, json, dotenv
from typing import Any, TypedDict

dotenv.load_dotenv()


def get_sk() -> str:
    return os.environ["SECRET_KEY"]


def get_e_web3() -> Web3:
    return Web3(Web3.HTTPProvider(os.environ["EVM_URL"]))


def get_c_web3() -> ConfluxWeb3:
    return ConfluxWeb3(ConfluxWeb3.HTTPProvider(os.environ["CORE_URL"]))


class Metadata(TypedDict):
    abi: Any
    bytecode: Any


def get_metadata(name: str) -> Metadata:
    with open(f"build/contracts/{name}.json") as f:
        d = json.load(f)
        return {
            "abi": d["abi"],
            "bytecode": d["bytecode"]
        }


def main():
    c_web3 = get_c_web3()
    e_web3 = get_e_web3()
    c_web3.cfx.default_account = c_web3.account.from_key(get_sk())
    e_account = e_web3.eth.account.from_key(get_sk())
    e_web3.middleware_onion.add(construct_sign_and_send_raw_middleware(e_account))
    e_web3.eth.default_account = e_account.address
    
    csc_address = c_web3.cfx.contract(name="CrossSpaceCall").address
    sponsor_whitelist_control = c_web3.cfx.contract(name="SponsorWhitelistControl", with_deployment_info=True)
    name = os.environ["CORE_CONTRACT_NAME"]
    symbol = os.environ["CORE_CONTRACT_SYMBOL"]
    default_oracle_life = int(os.environ["DEFAULT_ORACLE_LIFE"])

    DualSpaceNFTCore = c_web3.cfx.contract(**get_metadata("DualSpaceNFTCore"))
    DualSpaceNFTEvm = e_web3.eth.contract(**get_metadata("DualSpaceNFTEvm"))
    DeploymentProxyCore = c_web3.cfx.contract(**get_metadata("DeploymentProxy"))
    DeploymentProxyEvm = e_web3.eth.contract(**get_metadata("DeploymentProxy"))
    espace_chain_id = e_web3.eth.chain_id
    
    print(f"deploying...")
    core_impl_addr = DualSpaceNFTCore.constructor().transact().executed()["contractCreated"]
    print(f"core contract impl deployed at {core_impl_addr}")
    core_contract = DualSpaceNFTCore(DeploymentProxyCore.constructor(core_impl_addr, "0x").transact().executed()["contractCreated"])
    print(f"core contract proxy deployed at {core_contract.address}")
    
    evm_impl_addr = e_web3.eth.wait_for_transaction_receipt(DualSpaceNFTEvm.constructor().transact({
        "gasPrice": 2 * 10 **10
    }))["contractAddress"]
    print(f"evm contract impl deployed at {evm_impl_addr}")
    evm_contract = DualSpaceNFTEvm(e_web3.eth.wait_for_transaction_receipt(DeploymentProxyEvm.constructor(evm_impl_addr, "0x").transact({
        "gasPrice": 2 * 10 **10
    }))["contractAddress"])
    print(f"evm contract proxy deployed at {evm_contract.address}")
    
    print("initializing contracts...")
    mapped_address = c_web3.address.calculate_mapped_evm_space_address(core_contract.address)
    evm_contract.functions.initialize(
        name, symbol, mapped_address
    ).transact({
        "gasPrice": 2 * 10 **10
    })
    core_contract.functions.initialize(
        name, symbol, evm_contract.address, csc_address, espace_chain_id, default_oracle_life
    ).transact().executed()
    
    print("setting sponsor...")
    sponsor_whitelist_control.functions.addPrivilegeByAdmin(core_contract.address, [c_web3.address.zero_address()]).transact().executed()
    sponsor_whitelist_control.functions.setSponsorForCollateral(core_contract.address).transact({
        "value": 5 * 10**19
    }).executed()
    sponsor_whitelist_control.functions.setSponsorForGas(core_contract.address, 10**16).transact({
        "value": 10**19
    }).executed()

if __name__ == "__main__":
    main()
