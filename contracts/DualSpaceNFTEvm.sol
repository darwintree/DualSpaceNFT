// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

// import "@openzepplin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "./DualSpaceGeneral.sol";

// deployment
// firstly core side contract
// then deploy espace contract with core side contract mapping address (bind from espace->core)
// finally bind from core (bind from core->espace)
contract DualSpaceNFTEvm is DualSpaceGeneral {

    address _coreContractMappingAddress;
    // the token should be able to move directly at espace only if the core space owner is not set
    // or after 
    mapping(uint256=>bool) _evmTransferable;

    struct ExpirationSetting {
        uint startBlock;
        uint8 ratio;
    }

    // token batch setting is placed at espace for dual space visit
    mapping (uint128=>ExpirationSetting) _batchExpirationSetting;
    uint _baseExpirationBlockInterval;

    // name_ and symbol_ should be same as core side
    constructor(string memory name_, string memory symbol_, address _coreContractMappingAddress_) ERC721(name_, symbol_) {
        _coreContractMappingAddress = _coreContractMappingAddress_;
        _baseExpirationBlockInterval = 30 days * 2; // 2 block per second
    }

    modifier fromCore() {
        require(msg.sender == _coreContractMappingAddress, "only core contract could manipulate this function");
        _;
    }

    function mint(bytes20 ownerEvmAddress, uint256 tokenId) public fromCore {
        // uint128 batchNbr = _resolveTokenId(tokenId).batchNbr;
        // require(_batchExpirationSetting[batchNbr].startBlock != 0, "batch is not start");
        _mint(address(ownerEvmAddress), tokenId);
    }

    function resolveTokenId(uint256 tokenId) public view returns (TokenMeta memory) {
        require (_exists(tokenId), "token id does not exist");
        TokenMeta memory tokenMeta = _resolveTokenId(tokenId);
        return tokenMeta;
    }

    function getExpiration(uint256 tokenId) public view override returns (uint256 exp){
        TokenMeta memory tokenMeta = _resolveTokenId(tokenId);
        ExpirationSetting memory expSetting = _batchExpirationSetting[tokenMeta.batchNbr];
        exp = expSetting.startBlock + expSetting.ratio * tokenMeta.rarity * _baseExpirationBlockInterval;
    }

    function startBatch(uint128 batchNbr, uint8 ratio) public fromCore {
        _batchExpirationSetting[batchNbr] = ExpirationSetting(block.number, ratio);
        emit BatchStart(block.number, batchNbr, ratio);
    }

    // Indeed, this is not a "transfer" action because the owner should be one entity but with different address
    function setEvmOwner(bytes20 ownerEvmAddress, uint256 tokenId) public fromCore {
        // don't need to use safeTransferFrom because will not be locked
        _transfer(ownerOf(tokenId), address(ownerEvmAddress), tokenId);
    }

    function setTransferableTable(uint256 tokenId, bool transferable) public fromCore {
        _evmTransferable[tokenId] = transferable;
    }

    function _isEvmTransferable(uint256 tokenId) internal view returns (bool) {
        return _evmTransferable[tokenId];
    }

    function safeTransferFrom(address from, address to, uint256 tokenId) public override {
        require(_isEvmTransferable(tokenId), "This token is not transferable because its core space owner is set. Clear core space owner and try again");
        super.safeTransferFrom(from, to, tokenId);
    }
}