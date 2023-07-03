// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;
import "./EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

abstract contract EvmMetatransactionVerifier is EIP712 {

    // avoid meta transaction replay attack
    mapping (bytes20=>uint256) _metaTransactionNonces;

    constructor(string memory name, string memory version, uint256 eSpaceChainId) EIP712(name, version, eSpaceChainId) {

    }

    function getMetatransactionNonce(bytes20 evmAddress) public view returns (uint256) {
        return _metaTransactionNonces[evmAddress];
    }

    function isOverwhelminglySameAddress(address coreAddress, bytes20 rawEvmAddress) public pure returns (bool) {
        // core address and evm address differs for first 4 bits
        uint160 result = (uint160(coreAddress) ^ uint160(rawEvmAddress)) & uint160(0x0fffFFFFFfFfffFfFfFFffFffFffFFfffFfFFFFf);
        return result == 0;
    }

    function _recoverWithNonceChange(bytes memory signature, bytes20 evmSigner, uint256 tokenId, address newCoreOwner) internal returns (bool) {
        bytes32 digest = _hashTypedDataV4(
            keccak256(
                abi.encode(
                    keccak256("EvmMetatransaction(uint256 metatransactionNonce,uint256 tokenId,address newCoreOwner)"), getMetatransactionNonce(evmSigner), tokenId, newCoreOwner
                )
            )
        );
        address firstHexReplacedEvmSigner = ECDSA.recover(digest, signature);

        require(isOverwhelminglySameAddress(firstHexReplacedEvmSigner, evmSigner), "signature does not match evmSigner");
        _metaTransactionNonces[evmSigner] += 1;
        return true;
    }
}