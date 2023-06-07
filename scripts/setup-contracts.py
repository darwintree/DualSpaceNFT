from brownie import (
    MockCrossSpaceCall, # type:ignore # ContractContainer
    DualSpaceNFTCore, # type:ignore
    DualSpaceNFTEvm, # type:ignore
    MockMappedAddress, # type:ignore
    accounts,
    web3
)
from brownie.network.contract import Contract, ContractContainer
from brownie.network.account import Accounts, Account
from typing import cast, Callable
from brownie.exceptions import (
    VirtualMachineError,
)


def should_revert(expected_revert_msg: str, f: Callable, *args, **kwargs):
    try:
        f(*args, **kwargs)
    except VirtualMachineError as e:
        if expected_revert_msg:
            if expected_revert_msg not in e.message:
                raise Exception(
                    f"no expected string in exception: {expected_revert_msg}"
                )
        return
    else:
        raise Exception("expect to fail")


def main():
    # accounts = cast(Accounts, accounts)
    owner = accounts[0]
    oracle_signer = accounts[1]
    user = accounts[2]
    random_sender = accounts[3]
    evm_user = accounts[4]
    core_another_address = accounts[5].address
    evm_another_address = accounts[6].address
    name = "NAME"
    symbol = "symbol"
    batch_nbr = 20230401

    # setup
    cross_space_call = cast(Contract, MockCrossSpaceCall.deploy({"from": owner}))
    core_contract = cast(
        Contract,
        DualSpaceNFTCore.deploy(
            name, symbol, cross_space_call.address, {"from": owner}
        ),
    )
    mapped_address = cast(
        Contract, MockMappedAddress.deploy(core_contract.address, {"from": owner})
    ).address
    cross_space_call.setMockMapped(core_contract.address, mapped_address)
    evm_contract = cast(
        Contract, DualSpaceNFTEvm.deploy(name, symbol, mapped_address, {"from": owner})
    )
    core_contract.setEvmContractAddress(evm_contract.address, {"from": owner})

    # start batch
    core_contract.startBatch(batch_nbr, oracle_signer, 1, {"from": owner})

    # print("should fail because permission is not granted")
    should_revert(
        "",
        core_contract.mint.call,
        batch_nbr,
        "hello_poap",
        user,
        evm_user.address,
        0x00,
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
        "",
        core_contract.mint.call,
        batch_nbr,
        "hello_poap",
        user,
        evm_user.address,
        0x00,
        {"from": random_sender},
    )
    # core_contract.mint(
    #     batch_nbr, "hello_poap", user, evm_user.address, 0x00, {"from": random_sender}
    # )

    # print(evm_contract.getExpiration(20230401010001).traceback())
    print(evm_contract.getExpiration(token_id))
    assert core_contract.isExpired(token_id) == False

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
    core_contract.setEvmOwner(token_id, evm_another_address,  {"from": user})
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
    assert web3.toChecksumAddress(core_contract.evmOwnerOf(token_id)) == evm_contract.address
    core_contract.safeTransferFrom(user, core_another_address, token_id, {"from": user})
    assert core_contract.ownerOf(token_id) == core_another_address
    
    # test transfer evm
    core_contract.setEvmOwner(token_id, evm_user.address, {"from": core_another_address})
    assert evm_contract.ownerOf(token_id) == evm_user.address
    should_revert(
        "not transferable because its core space owner is set",
        evm_contract.safeTransferFrom.call,
        evm_user,
        evm_another_address,
        token_id,
    )
    signature = 0x00
    tx = core_contract.clearCoreOwner(token_id, signature, { "from": random_sender })
    assert core_contract.ownerOf(token_id) == core_contract.address
    # print(tx.call_trace())
    # print("evm token can transfer:")
    # print(evm_contract._isEvmTransferable(token_id))
    evm_contract.safeTransferFrom(evm_user, evm_another_address, token_id, { 'from': evm_user })
    assert evm_contract.ownerOf(token_id) == evm_another_address
    
    signature = 0x00
    core_contract.setCoreOwner(token_id, user, signature, { 'from': random_sender })
    should_revert(
        "not transferable because its core space owner is set",
        evm_contract.safeTransferFrom.call,
        evm_another_address,
        evm_user,
        token_id,
    )


def mint_to(
    core_contract: Contract,
    batch_nbr: int,
    oracle_signer: Account,
    username: str,
    rarity: int,
    core_owner: Account | None,
    evm_owner: Account | None,
    random_sender: Account,
) -> int:
    core_contract.batchAuthorizeMintPermission(
        batch_nbr, [username], rarity, {"from": oracle_signer}
    )

    core_address = core_owner.address if core_owner else "0x0000000000000000"
    evm_address = evm_owner.address if evm_owner else "0x0000000000000000"
    token_id = core_contract.mint.call(
        batch_nbr,
        "hello_poap",
        core_address,
        evm_address,
        0x00,
        {"from": random_sender},
    )
    mint_tx = core_contract.mint(
        batch_nbr,
        "hello_poap",
        core_address,
        evm_address,
        0x00,
        {"from": random_sender},
    )
    # print(mint_tx.events)
    return token_id
