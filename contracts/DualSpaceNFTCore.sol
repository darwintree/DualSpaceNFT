// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

// import "@openzepplin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "../interfaces/ICrossSpaceCall.sol";

// deployment
// firstly core side contract
// then deploy espace contract with core side contract mapping address (bind from espace->core)
// finally bind from core (bind from core->espace)
contract DualSpaceNFTCore is ERC721, Ownable {
    bytes20 evmContractAddress;
    address admin;
    CrossSpaceCall crossSpaceCall;
    // 20230523 => address
    // mint oracle is a centralized server to prove the user owns the Github token
    mapping (uint32=>address) mintOracleSigner;
    // avoid replay attack
    mapping (bytes20=>uint256) crossSpaceNonce;
    mapping (uint256=>bool) coreTransferable;

    constructor(string memory name_, string memory symbol_) ERC721(name_, symbol_) Ownable() {
        crossSpaceCall = CrossSpaceCall(0x0888000000000000000000000000000000000006);
    }

    function setEvmContractAddress(bytes20 evmContractAddress_) public onlyOwner {
        require(evmContractAddress != bytes20(0), "setEvmContractAddress should only be invoked once");
        evmContractAddress = evmContractAddress_;
    }

    function setMintOracleSigner(uint32 batch, address signer) public onlyOwner() {
        mintOracleSigner[batch] = signer;
    }

    function isCoreTransferable(uint256 tokenId) internal view returns (bool) {
        bytes20 currentEvmOwner = bytes20(crossSpaceCall.staticCallEVM(evmContractAddress, 
            abi.encodeWithSignature("ownerOf(uint256)", tokenId)
        ));
        return currentEvmOwner == evmContractAddress;
    }

    // setOwner is different from 
    function setEvmOwner(bytes20 ownerEvmAddress, uint256 tokenId) public {
        crossSpaceCall.callEVM(evmContractAddress, 
            abi.encodeWithSignature("setEvmOwner(bytes20, uint256)", ownerEvmAddress, tokenId)
        );
    }

    function setCoreOwner(address ownerCoreAddress, uint256 tokenId, string memory signatureFromEvmAddress) public {
        // TODO: verify signatureFromEvmAddress is a valid signature signed by evm owner
        // ...
        _transfer(ownerOf(tokenId), ownerCoreAddress, tokenId);
    }


    function safeTransferFrom(address from, address to, uint256 tokenId) public override {
        require(isCoreTransferable(tokenId), "This token is not transferable because its evm space owner is set. Clear evm space owner and try again");
        super.safeTransferFrom(from, to, tokenId);
    }

    function _transfer(address from, address to, uint256 tokenId) internal virtual override {
        if (from == address(this) && from != to) {
            crossSpaceCall.callEVM(evmContractAddress, 
                abi.encodeWithSignature("setTransferableTable(uint256,bool)", tokenId, true)
            );
        }
        if (to == address(this)) {
            crossSpaceCall.callEVM(evmContractAddress, 
                abi.encodeWithSignature("setTransferableTable(uint256,bool)", tokenId, false)
            );
        }
        super._transfer(from, to, tokenId);
    }
}
