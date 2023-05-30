// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

// import "@openzepplin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

// deployment
// firstly core side contract
// then deploy espace contract with core side contract mapping address (bind from espace->core)
// finally bind from core (bind from core->espace)
contract DualSpaceNFTEvm is ERC721 {

    address coreContractMappingAddress;
    // the token should be able to move directly at espace only if the core space owner is not set
    // or after 
    mapping(uint256=>bool) evmTransferable;

    // name_ and symbol_ should be same as core side
    constructor(string memory name_, string memory symbol_, address coreContractMappingAddress_) ERC721(name_, symbol_) {
        coreContractMappingAddress = coreContractMappingAddress_;
    }

    modifier fromCore() {
        require(msg.sender == coreContractMappingAddress, "only core contract could manipulate this function");
        _;
    }

    // Indeed, this is not a "transfer" action because the owner should be one entity but with different address
    function setEvmOwner(bytes20 ownerEvmAddress, uint256 tokenId) public fromCore {
        // don't need to use safeTransferFrom because will not be locked
        _transfer(ownerOf(tokenId), address(ownerEvmAddress), tokenId);
    }

    function setTransferableTable(uint256 tokenId, bool transferable) public fromCore {
        evmTransferable[tokenId] = transferable;
    }

    function isEvmTransferable(uint256 tokenId) internal view returns (bool) {
        return evmTransferable[tokenId];
    }

    function safeTransferFrom(address from, address to, uint256 tokenId) public override {
        require(isEvmTransferable(tokenId), "This token is not transferable because its core space owner is set. Clear core space owner and try again");
        super.safeTransferFrom(from, to, tokenId);
    }
}