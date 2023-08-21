// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@ozori/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract DeploymentProxy is ERC1967Proxy {
    constructor(address implementation, bytes memory data) payable ERC1967Proxy(implementation, data) {
    }
}