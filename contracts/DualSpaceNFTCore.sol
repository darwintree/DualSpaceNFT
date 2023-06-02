// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

// import "@openzepplin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
// import "OpenZeppelin/openzeppelin-contracts@4.9.0/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "../interfaces/ICrossSpaceCall.sol";

// deployment
// firstly core side contract
// then deploy espace contract with core side contract mapping address (bind from espace->core)
// finally bind from core (bind from core->espace)
contract DualSpaceNFTCore is ERC721, Ownable {
    bytes20 _evmContractAddress;
    CrossSpaceCall _crossSpaceCall;
    uint _defaultOracleLife;
    struct MintOracleSetting {
        address signer;
        uint expiration;
    }

    // 20230523 => address
    // mint oracle is a centralized server to prove the user owns the Github token
    mapping (uint32=>MintOracleSetting) _mintOracleSignerSetting;
    // batchNbr => usernameHash => rarityCouldMint
    mapping (uint32=>mapping(bytes32=>uint8)) _authorizedRarityMintPermission;
    // avoid meta transaction replay attack
    mapping (bytes20=>uint256) _crossSpaceNonce;
    mapping (uint32=>uint16) _batchInternalIdCounter;

    constructor(string memory name_, string memory symbol_) ERC721(name_, symbol_) Ownable() {
        _crossSpaceCall = CrossSpaceCall(0x0888000000000000000000000000000000000006);
        _defaultOracleLife = 30 days;
    }

    function setEvmContractAddress(bytes20 evmContractAddress_) public onlyOwner {
        require(_evmContractAddress == bytes20(0), "setEvmContractAddress should only be invoked once");
        _evmContractAddress = evmContractAddress_;
    }

    // function authorizeMintOracleSigner(uint32 batchNbr, address signer, ) public onlyOwner {
    //     _mintOracleSignerSetting[batchNbr].signer = signer;
    //     _mintOracleSignerSetting[batchNbr].expiration = block.number + _defaultOracleLife;
    // }
    event BatchStart(uint256 startTimestamp, uint32 batchNbr, uint8 ratio);

    function startBatch(uint32 batchNbr, address signer, uint8 ratio) public onlyOwner {
        require(batchNbr < 99999999, "invalid batch nbr");
        _mintOracleSignerSetting[batchNbr].signer = signer;
        _mintOracleSignerSetting[batchNbr].expiration = block.number + _defaultOracleLife;
        _crossSpaceCall.callEVM(_evmContractAddress, 
            abi.encodeWithSignature("startBatch(uint32,uint8)", batchNbr, ratio)
        );
        emit BatchStart(block.number, batchNbr, ratio);
    }

    function _isValidMintOracleSigner(address signer, uint32 batchNbr) internal view returns (bool) {
        return signer == _mintOracleSignerSetting[batchNbr].signer && _mintOracleSignerSetting[batchNbr].expiration > block.number;
    }

    function batchAuthorizeMintPermission(uint32 batchNbr, string[] memory usernames, uint8 rarity) public {
        // owner or mint oracle
        if (msg.sender == owner()) {
            // do nothing
        } else if (
            _isValidMintOracleSigner(msg.sender, batchNbr)
        ) {
            // do nothing
        }
        else {
            revert("msg sender is not authorized to set mint permission");
        }
        for (uint256 i = 0; i < usernames.length; i++) {
            _authorizeMintPermission(batchNbr, usernames[i], rarity);
        }
    }

    function _authorizeMintPermission(uint32 batchNbr, string memory username, uint8 rarity) internal {
        bytes32 usernameHash = keccak256(abi.encodePacked(username));
        _authorizedRarityMintPermission[batchNbr][usernameHash] = rarity;
    }

    function _nextTokenId(uint32 batchNbr, uint8 rarity, uint16 batchInternalId) pure internal returns (uint256) {
        return batchNbr * 10**6 + rarity ** 10**4 + batchInternalId;
    }

    function mint(uint32 batchNbr, string memory username, address ownerCoreAddress, bytes20 ownerEvmAddress, bytes memory oracleSignature) public returns (uint256) {
        require(_mintOracleSignerSetting[batchNbr].expiration > block.number, "no available mint oracle at present");
        // TODO: verify signature is from oracle
        // signer = ecrecover

        bytes32 usernameHash = keccak256(abi.encodePacked(username));
        uint8 rarity = _authorizedRarityMintPermission[batchNbr][usernameHash];
        uint256 tokenId = _nextTokenId(batchNbr, rarity, _batchInternalIdCounter[batchNbr]);
        // if mint to zero, mint to self
        if (ownerCoreAddress == address(0)) {
            ownerCoreAddress = address(this);
        }
        if (ownerEvmAddress == bytes20(0)) {
            ownerEvmAddress = _evmContractAddress;
        }
        _mint(ownerCoreAddress, tokenId);
        // update transferable state
        if (ownerCoreAddress == address(this)) {
            _crossSpaceCall.callEVM(_evmContractAddress, 
                abi.encodeWithSignature("setTransferableTable(uint256,bool)", tokenId, true)
            );
        }
        _crossSpaceCall.callEVM(_evmContractAddress,
            abi.encodeWithSignature("mint(bytes20,uint256)", ownerEvmAddress, tokenId)
        );

        // postMint
        _batchInternalIdCounter[batchNbr] += 1;
        delete _authorizedRarityMintPermission[batchNbr][usernameHash];
        return tokenId;
    }

    // call 
    function isExpired(uint256 tokenId) public view returns(bool){
        return bytes1(_crossSpaceCall.staticCallEVM(_evmContractAddress, 
            abi.encodeWithSignature("isExpired(uint256)", tokenId)
        )) != bytes1(0x0);
    }

    function _isCoreTransferable(uint256 tokenId) internal view returns (bool) {
        bytes20 currentEvmOwner = bytes20(_crossSpaceCall.staticCallEVM(_evmContractAddress, 
            abi.encodeWithSignature("ownerOf(uint256)", tokenId)
        ));
        return currentEvmOwner == _evmContractAddress;
    }

    function clearEvmOwner(uint256 tokenId) public {
        setEvmOwner(_evmContractAddress, tokenId);
    }

    // only core owner can set evm owner
    function setEvmOwner(bytes20 ownerEvmAddress, uint256 tokenId) public {
        require(msg.sender == ownerOf(tokenId), "caller is not core token owner");
        _crossSpaceCall.callEVM(_evmContractAddress, 
            abi.encodeWithSignature("setEvmOwner(bytes20, uint256)", ownerEvmAddress, tokenId)
        );
    }

    function setCoreOwner(address ownerCoreAddress, uint256 tokenId, string memory signatureFromEvmAddress) public {
        // TODO: verify signatureFromEvmAddress is a valid signature signed by evm owner
        // ...
        _transfer(ownerOf(tokenId), ownerCoreAddress, tokenId);
    }


    function safeTransferFrom(address from, address to, uint256 tokenId) public override {
        require(_isCoreTransferable(tokenId), "This token is not transferable because its evm space owner is set. Clear evm space owner and try again");
        super.safeTransferFrom(from, to, tokenId);
    }

    function _transfer(address from, address to, uint256 tokenId) internal virtual override {
        if (from == address(this) && from != to) {
            _crossSpaceCall.callEVM(_evmContractAddress, 
                abi.encodeWithSignature("setTransferableTable(uint256,bool)", tokenId, true)
            );
        }
        if (to == address(this)) {
            _crossSpaceCall.callEVM(_evmContractAddress, 
                abi.encodeWithSignature("setTransferableTable(uint256,bool)", tokenId, false)
            );
        }
        super._transfer(from, to, tokenId);
    }
}
