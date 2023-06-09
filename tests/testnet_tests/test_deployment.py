from conflux_web3 import Web3 as CWeb3 # do hook

import os, pytest, json
from typing import cast, Tuple
from dotenv import load_dotenv

from eth_account import Account
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from web3.contract.contract import Contract
from web3 import Web3, HTTPProvider

from cfx_utils.types import ChecksumAddress
from cfx_address import Base32Address
from cfx_account import Account as CfxAccount
from conflux_web3.contract import ConfluxContract

def test_owner(c_w3: CWeb3, core_contract: ConfluxContract, evm_contract: ConfluxContract):
    owner = core_contract.functions.owner().call()
    assert(owner == c_w3.cfx.default_account)
