from conflux_web3 import Web3 as CWeb3  # do hook

import os, pytest, json
from typing import cast, Tuple, List
from dataclasses import dataclass
from dotenv import load_dotenv

from eth_account import Account
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from web3.contract.contract import Contract
from web3 import Web3, HTTPProvider

from cfx_utils.types import ChecksumAddress
from cfx_address import Base32Address
from cfx_account import Account as CfxAccount
from cfx_account import LocalAccount as CfxLocalAccount
from conflux_web3.contract import ConfluxContract

from conftest import BatchSetting


@dataclass
class MintPermission:
    username: str
    rarity: int


@pytest.fixture(scope="module")
def mint_permissions() -> List[MintPermission]:
    return [MintPermission("hello_poap", 1), MintPermission("goodbye", 2)]


@pytest.fixture(scope="module")
def authorized_usernames(
    core_contract: ConfluxContract,
    batch_setting: BatchSetting,
    mint_permissions: List[MintPermission],
) -> List[str]:
    # test authorize via owner
    core_contract.functions.batchAuthorizeMintPermission(
        batch_setting.batch_nbr,
        [mint_permissions[0].username],
        [mint_permissions[0].rarity],
    ).transact().executed()
    # test authorize via oracle signer
    core_contract.functions.batchAuthorizeMintPermission(
        batch_setting.batch_nbr,
        [mint_permissions[1].username],
        [mint_permissions[1].rarity],
    ).transact({"from": batch_setting.signer.address}).executed()
    return [x.username for x in mint_permissions]


def test_random_authorize_username(
    core_contract: ConfluxContract,
    batch_setting: BatchSetting,
    random_core_sender: CfxLocalAccount,
    mint_permissions: List[MintPermission],
):
    username = "hello_poap"
    rarity = 1
    # should fail
    with pytest.raises(Exception):
        core_contract.functions.batchAuthorizeMintPermission(
            batch_setting.batch_nbr, [username], [rarity]
        ).transact({"from": random_core_sender.address}).executed()


# not availble
def test_mint(
    c_w3: CWeb3,
    core_contract: ConfluxContract,
    user_private_key: bytes,
    batch_setting: BatchSetting,
    authorized_usernames: List[str],
    oracle_signer: CfxLocalAccount,
):
    username = authorized_usernames[0]
    core_user_address = cast(Base32Address, c_w3.account.from_key(user_private_key).address)
    
    message_hash = Web3.solidity_keccak(
        ["uint128", "bytes32", "address", "address"],
        [
            batch_setting.batch_nbr,
            Web3.solidity_keccak(["string"], [username]),
            core_user_address.hex_address,
            core_user_address.hex_address,
        ],
    )
    
    signature = Account.signHash(
        message_hash,
        oracle_signer.key,
    )
    
    
    token_id = cast(int, core_contract.functions.mint(
        batch_setting.batch_nbr,
        username,
        core_user_address,
        core_user_address.hex_address,
        [ signature.v, hex(signature.r), hex(signature.s) ], # signature
    ).call())
    receipt = core_contract.functions.mint(
        batch_setting.batch_nbr,
        username,
        core_user_address,
        core_user_address.hex_address,
        [ signature.v, hex(signature.r), hex(signature.s) ], # signature
    ).transact().executed()
    token_owner = core_contract.functions.ownerOf(token_id).call()
    assert token_owner == core_user_address
