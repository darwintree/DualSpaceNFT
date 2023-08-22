from brownie import (
    MockCrossSpaceCall,  # type:ignore # ContractContainer
    DualSpaceNFTCore,  # type:ignore
    DualSpaceNFTEvm,  # type:ignore
    MockMappedAddress,  # type:ignore
    DeploymentProxy, # type: ignore
    accounts as untyped_accounts,
    web3,
    chain,
)

from brownie.network.contract import Contract, ContractContainer
from brownie.network.account import Account, Accounts, _PrivateKeyAccount, LocalAccount
from typing import cast, Callable, List, Mapping, Union
from brownie.exceptions import (
    VirtualMachineError,
)

from eth_account import (
    Account as EthAccount,
)
from eth_account.messages import encode_structured_data, SignableMessage
from eth_account.datastructures import (
    SignedMessage,
)


def should_revert(expected_revert_msg: str, f: Callable, *args, **kwargs):
    try:
        f(*args, **kwargs)
    except VirtualMachineError as e:
        if expected_revert_msg:
            if expected_revert_msg not in e.message:
                print(e)
                raise Exception(
                    f"no expected string in exception: {expected_revert_msg}"
                )
        return
    else:
        raise Exception("expect to fail")


def main():
    accounts = cast(Accounts, untyped_accounts)
    owner = accounts[0]
    # oracle_signer = accounts[1]
    oracle_signer = accounts.add()
    user = accounts[2]
    random_sender = accounts[3]
    evm_user = accounts.add()
    core_another_address = accounts[5].address
    evm_another_account = accounts.add()
    evm_another_address = evm_another_account.address
    authorizer = accounts.add()
    name = "NAME"
    symbol = "symbol"
    batch_nbr = 20230401
    espace_chain_id = web3.eth.chain_id
    oracle_expiration = 1000 # should set to 30 * 24 * 60 * 60 * 2 in deployment env

    owner.transfer(evm_user, "1 ether")  # type: ignore
    owner.transfer(evm_another_address, "1 ether")  # type: ignore

    # setup
    cross_space_call = cast(Contract, MockCrossSpaceCall.deploy({"from": owner}))
    core_contract_impl = cast(
        Contract,
        DualSpaceNFTCore.deploy({"from": owner}),
    )
    core_contract_proxy = cast(Contract, DeploymentProxy.deploy(core_contract_impl.address, bytes(0), {"from": owner}))
    addr = core_contract_proxy.address
    DeploymentProxy.remove(DeploymentProxy[-1])
    core_contract = DualSpaceNFTCore.at(core_contract_proxy.address)

    mapped_address = cast(
        Contract, MockMappedAddress.deploy(core_contract.address, {"from": owner})
    ).address
    cross_space_call.setMockMapped(core_contract.address, mapped_address)
    evm_contract_impl = cast(
        Contract, DualSpaceNFTEvm.deploy({"from": owner})
    )
    evm_contract_proxy = cast(Contract, DeploymentProxy.deploy(evm_contract_impl.address, bytes(0), {"from": owner}))
    addr = evm_contract_proxy.address
    DeploymentProxy.remove(DeploymentProxy[-1])
    evm_contract = cast(Contract, DualSpaceNFTEvm.at(addr))

    evm_contract.initialize(name, symbol, mapped_address, {"from": owner})
    core_contract.initialize(
        name, symbol, evm_contract.address, cross_space_call.address, espace_chain_id, oracle_expiration, {"from": owner} # set life to 1000 for tests
    )
    
    # test upgrade
    new_core_implementation = DualSpaceNFTCore.deploy({"from": owner})
    new_evm_implementation = DualSpaceNFTEvm.deploy({"from": owner})
    core_contract.upgradeTo(new_core_implementation.address, {"from": owner})
    should_revert(
        "caller is not the owner",
        core_contract.upgradeTo.call,
        new_core_implementation.address,
        {"from": oracle_signer}
    )
    core_contract.upgradeEvmContractTo(new_evm_implementation.address, {"from": owner})
    should_revert(
        "caller is not the owner",
        core_contract.upgradeEvmContractTo.call,
        new_evm_implementation.address,
        {"from": oracle_signer}
    )
    should_revert(
        "only core contract could manipulate this function",
        evm_contract.upgradeTo.call,
        new_core_implementation.address,
        {"from": oracle_signer}
    )

    # start batch
    core_contract.startBatch(batch_nbr, oracle_signer, authorizer, 1, {"from": owner})

    # print("should fail because permission is not granted")
    should_revert(
        "no permission to mint",
        core_contract.mint.call,
        batch_nbr,
        "hello_poap",
        user,
        evm_user.address,
        (0, "0x00", "0x00"),
        {"from": random_sender},
    )
    # core_contract.mint(
    #     batch_nbr, "hello_poap", user, evm_user.address, 0x00, {"from": random_sender}
    # )

    # mint test
    token_id = mint_to(
        core_contract,
        batch_nbr,
        oracle_signer,
        authorizer,
        "hello_poap",
        1,
        user,
        evm_user,
        random_sender,
    )

    assert core_contract.ownerOf(token_id) == user.address
    assert evm_contract.ownerOf(token_id) == evm_user.address

    # print("should fail because permission is consumed")
    should_revert(
        "no permission to mint",
        core_contract.mint.call,
        batch_nbr,
        "hello_poap",
        user,
        evm_user.address,
        (0, "0x00", "0x00"),
        {"from": random_sender},
    )
    # core_contract.mint(
    #     batch_nbr, "hello_poap", user, evm_user.address, 0x00, {"from": random_sender}
    # )

    # print(evm_contract.getPrivilegeExpiration(20230401010001).traceback())
    print(evm_contract.getPrivilegeExpiration(token_id))
    assert core_contract.isPrivilegeExpired(token_id) == False

    # test safeTransferFrom is banned until another side owner is reset
    should_revert(
        "not transferable because its evm space owner is set",
        core_contract.safeTransferFrom.call,
        user,
        core_another_address,
        token_id,
    )
    should_revert(
        "not transferable because its core space owner is set",
        evm_contract.safeTransferFrom.call,
        evm_user,
        evm_another_address,
        token_id,
    )

    # test set evm owner
    # should revert because is not owner
    should_revert(
        "caller is not core token owner",
        core_contract.setEvmOwner.call,
        token_id,
        evm_another_address,
        {"from": evm_another_address},
    )

    assert core_contract.ownerOf(token_id) == user.address
    core_contract.setEvmOwner(token_id, evm_another_address, {"from": user})
    assert evm_contract.ownerOf(token_id) == evm_another_address

    # test core transferable after evm owner is cleared
    should_revert(
        "caller is not core token owner",
        core_contract.clearEvmOwner.call,
        token_id,
        {"from": core_another_address},
    )
    core_contract.clearEvmOwner(token_id, {"from": user})
    assert evm_contract.ownerOf(token_id) == evm_contract.address
    assert (
        web3.toChecksumAddress(core_contract.evmOwnerOf(token_id))
        == evm_contract.address
    )
    core_contract.safeTransferFrom(user, core_another_address, token_id, {"from": user})
    assert core_contract.ownerOf(token_id) == core_another_address

    # test transfer evm
    core_contract.setEvmOwner(
        token_id, evm_user.address, {"from": core_another_address}
    )
    assert evm_contract.ownerOf(token_id) == evm_user.address
    should_revert(
        "not transferable because its core space owner is set",
        evm_contract.safeTransferFrom.call,
        evm_user,
        evm_another_address,
        token_id,
    )
    metatransaction_constructor = MetatransactionConstructor(
        web3.eth.chain_id,
        name,
        "v1",
        core_contract,
    )

    clear_core_owner_metatransaction = (
        metatransaction_constructor.construct_eip712_message(
            evm_user.address,
            token_id,
            core_contract.address,  # set as evm_contract address to clear
        )
    )

    signed_metatransaction: SignedMessage = EthAccount.sign_message(
        clear_core_owner_metatransaction, evm_user.private_key
    )
    tx = core_contract.clearCoreOwner(
        evm_user.address,
        token_id,
        signed_metatransaction.signature,
        {"from": random_sender},
    )
    assert core_contract.ownerOf(token_id) == core_contract.address
    # print(tx.call_trace())
    # print("evm token can transfer:")
    # print(evm_contract._isEvmTransferable(token_id))
    evm_contract.safeTransferFrom(
        evm_user, evm_another_address, token_id, {"from": evm_user}
    )
    assert evm_contract.ownerOf(token_id) == evm_another_address

    core_contract.setCoreOwner(
        evm_another_address,
        token_id,
        user,
        EthAccount.sign_message(
            metatransaction_constructor.construct_eip712_message(
                evm_another_address,
                token_id,
                user.address,
            ),
            evm_another_account.private_key,
        ).signature,
        {"from": random_sender},
    )
    should_revert(
        "not transferable because its core space owner is set",
        evm_contract.safeTransferFrom.call,
        evm_another_address,
        evm_user,
        token_id,
    )
    
    mint_to(
        core_contract,
        batch_nbr,
        oracle_signer,
        authorizer,
        "hello_poap",
        1,
        user,
        None,
        random_sender,
    )
    
    mint_to(
        core_contract,
        batch_nbr,
        oracle_signer,
        authorizer,
        "hello_poap",
        1,
        None,
        evm_user,
        random_sender,
    )
    
    should_revert(
        "cannot clear both space owner when minting",
        mint_to,
        core_contract,
        batch_nbr,
        oracle_signer,
        authorizer,
        "hello_poap",
        1,
        None,
        None,
        random_sender,
    )

    core_contract.setBaseURI("https://baidu.com/", { "from": owner })
    assert core_contract.tokenURI(token_id) == evm_contract.tokenURI(token_id)

    should_revert(
        "mint setting not expired for enough time",
        core_contract.clearMintSetting.call,
        batch_nbr,
        {"from": random_sender},
    )
    chain.mine(oracle_expiration)
    should_revert(
        "mint setting not expired for enough time",
        core_contract.clearMintSetting.call,
        batch_nbr,
        {"from": random_sender},
    )
    chain.mine(oracle_expiration)
    core_contract.clearMintSetting(batch_nbr, {"from": random_sender})


class MetatransactionConstructor:
    def __init__(self, chain_id: int, name: str, version: str, contract: Contract):
        self.name = name
        self.version = version
        self.contract = contract
        self.chain_id = chain_id

    def construct_eip712_message(
        self, evm_signer_address: str, token_id: int, new_owner_address: str
    ) -> SignableMessage:
        raw_json = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "EvmMetatransaction": [
                    {"name": "metatransactionNonce", "type": "uint256"},
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "newCoreOwner", "type": "address"},
                ],
            },
            "primaryType": "EvmMetatransaction",
            "domain": {
                "name": self.name,
                "version": self.version,
                "chainId": self.chain_id,
                "verifyingContract": self.contract.address,
            },
            "message": {
                "metatransactionNonce": self.contract.getMetatransactionNonce(
                    evm_signer_address
                ),
                "tokenId": token_id,
                "newCoreOwner": new_owner_address,
            },
        }
        return encode_structured_data(raw_json)


def mint_to(
    core_contract: Contract,
    batch_nbr: int,
    oracle_signer: LocalAccount,
    authorizer: LocalAccount,
    username: str,
    rarity: int,
    core_owner: Union[_PrivateKeyAccount, None],
    evm_owner: Union[_PrivateKeyAccount, None],
    random_sender: _PrivateKeyAccount,
) -> int:
    core_contract.batchAuthorizeMintPermission(
        batch_nbr, [username], [rarity], {"from": authorizer}
    )

    core_address = core_owner.address if core_owner else "0x0000000000000000000000000000000000000000"
    evm_address = evm_owner.address if evm_owner else "0x0000000000000000000000000000000000000000"
    username_hash = web3.solidityKeccak(["string"], [username])
    message_hash = web3.solidityKeccak(
        ["uint128", "bytes32", "address", "address"],
        [
            batch_nbr,
            username_hash,
            core_address,
            evm_address,
        ],
    )
    signature: SignedMessage = EthAccount.signHash(
        message_hash, oracle_signer.private_key
    )
    token_id = core_contract.mint.call(
        batch_nbr,
        "hello_poap",
        core_address,
        evm_address,
        (
            signature.v,
            signature.r,
            signature.s,
        ),
        {"from": random_sender},
    )

    mint_tx = core_contract.mint(
        batch_nbr,
        "hello_poap",
        core_address,
        evm_address,
        (
            signature.v,
            signature.r,
            signature.s,
        ),
        {"from": random_sender},
    )
    # print(mint_tx.events)
    return token_id
