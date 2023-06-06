from brownie import (
    MockCrossSpaceCall, # ContractContainer
    DualSpaceNFTCore, 
    DualSpaceNFTEvm, 
    MockMappedAddress,
    accounts,
)
from brownie.network.contract import Contract, ContractContainer
from brownie.network.account import Accounts
from typing import cast

def main():
    # accounts = cast(Accounts, accounts)
    owner = accounts[0]
    oracle_signer = accounts[1]
    user = accounts[2]
    random_sender = accounts[3]
    evm_user = accounts[4]
    name = "NAME"
    symbol = 'symbol'
    batch_nbr = 20230401
    print(MockCrossSpaceCall.__class__)

    # setup
    cross_space_call = cast(Contract, MockCrossSpaceCall.deploy({ 'from': owner }))
    core_contract = cast(Contract, DualSpaceNFTCore.deploy(name, symbol, cross_space_call.address, { 'from': owner }))
    mapped_address = cast(Contract, MockMappedAddress.deploy(core_contract.address, { 'from': owner })).address
    cross_space_call.setMockMapped(core_contract.address, mapped_address)
    evm_contract = cast(Contract, DualSpaceNFTEvm.deploy(name, symbol, mapped_address, { 'from': owner }))
    core_contract.setEvmContractAddress(evm_contract.address, {'from': owner})
    
    # start batch
    core_contract.startBatch(batch_nbr, oracle_signer, 1, {'from': owner})
    # authorize mint permission
    core_contract.batchAuthorizeMintPermission(batch_nbr, ['hello_poap'], 1,  {'from': oracle_signer})
    
    # test mint
    mint_tx = core_contract.mint(batch_nbr, 'hello_poap', user, evm_user.address, 0x00, {'from': random_sender})
    print(mint_tx.events)
    assert core_contract.ownerOf(20230401010001) == user.address
    assert evm_contract.ownerOf(20230401010001) == evm_user.address
    print("should fail")
    mint_tx = core_contract.mint(batch_nbr, 'hello_poap', user, evm_user.address, 0x00, {'from': random_sender})
    
    # print(evm_contract.getExpiration(20230401010001).traceback())
    print(evm_contract.getExpiration(20230401010001))
    print(core_contract.isExpired(20230401010001))
    # test set
