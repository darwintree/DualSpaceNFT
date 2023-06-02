// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

// import "@openzepplin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";


// deployment
// firstly core side contract
// then deploy espace contract with core side contract mapping address (bind from espace->core)
// finally bind from core (bind from core->espace)
contract DualSpaceNFTEvm is ERC721 {

    address _coreContractMappingAddress;
    // the token should be able to move directly at espace only if the core space owner is not set
    // or after 
    mapping(uint256=>bool) _evmTransferable;


    struct TokenMeta {
        uint32 tokenBatch; // 20230401
        uint8 rarity;      // < 10
        uint16 batchInternalId; // < 999
    }
    struct ExpirationSetting {
        uint startTimestamp;
        uint8 ratio;
    }
    // token batch setting is placed at espace for dual space visit
    mapping (uint32=>ExpirationSetting) _batchExpirationSetting;
    uint _baseExpirationInternal;

    

    // name_ and symbol_ should be same as core side
    constructor(string memory name_, string memory symbol_, address _coreContractMappingAddress_) ERC721(name_, symbol_) {
        _coreContractMappingAddress = _coreContractMappingAddress_;
        _baseExpirationInternal = 30 days;
    }

    modifier fromCore() {
        // require(msg.sender == _coreContractMappingAddress, "only core contract could manipulate this function");
        _;
    }

    function mint(bytes20 ownerEvmAddress, uint256 tokenId) public fromCore {
        uint32 batchNbr = _resolveTokenId(tokenId).tokenBatch;
        require(_batchExpirationSetting[batchNbr].startTimestamp != 0, "batch is not start");
        _mint(address(ownerEvmAddress), tokenId);
    }

    // token example 20230401010001
    // token batch * 10^6 + rarity * 10^4 + batch internal id
    function _resolveTokenId(uint256 tokenId) internal pure returns (TokenMeta memory) {
        uint32 tokenBatch = uint32(tokenId/(10**6));
        uint8 rarity = uint8(tokenId/(10**4) - tokenBatch);
        uint16 batchInternalId = uint16(tokenId - tokenBatch * 10**6 - rarity * 10**4);
        return TokenMeta(tokenBatch, rarity, batchInternalId);
    }

    function isExpired(uint256 tokenId) public view returns (bool){
        TokenMeta memory tokenMeta = _resolveTokenId(tokenId);
        ExpirationSetting memory expSetting = _batchExpirationSetting[tokenMeta.tokenBatch];
        uint exp = expSetting.startTimestamp + expSetting.ratio * tokenMeta.rarity;
        return block.number < exp;
    }

    event BatchStart(uint256 startTimestamp, uint32 batchNbr, uint8 ratio);

    function startBatch(uint32 batchNbr, uint8 ratio) public fromCore {
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