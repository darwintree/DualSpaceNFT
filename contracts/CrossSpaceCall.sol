// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0;

// import "../ICrossSpaceCall.sol";
import "./MockMappedAddress.sol";

contract MockCrossSpaceCall {

    mapping(address=>bytes20) core2e;
    // mapping(bytes20=>address) e2core;

    function transferEVM(bytes20 to) external payable returns (bytes memory output) {
        address payable mappedAddress = payable(address(core2e[msg.sender]));
        require(mappedAddress != address(0), "mock mapped address is not set");
        return MockMappedAddress(mappedAddress).transferEVM{value: msg.value}(to);
    }

    function callEVM(bytes20 to, bytes calldata data) external payable returns (bytes memory output) {
        address payable mappedAddress = payable(address(core2e[msg.sender]));
        require(mappedAddress != address(0), "mock mapped address is not set");
        return MockMappedAddress(mappedAddress).callEVM{value: msg.value}(to, data);
    }

    function staticCallEVM(bytes20 to, bytes calldata data) external view returns (bytes memory output) {
        address payable mappedAddress = payable(address(core2e[msg.sender]));
        require(mappedAddress != address(0), "mock mapped address is not set");
        output = MockMappedAddress(mappedAddress).staticCallEVM(to, data);
    }

    function withdrawFromMapped(uint256 value) external {
        address payable mappedAddress = payable(address(core2e[msg.sender]));
        require(mappedAddress != address(0), "mock mapped address is not set");
        MockMappedAddress(mappedAddress).withdraw(value);
    }

    function mappedBalance(address addr) external view returns (uint256){
        // require(core2e[addr] != address(0))
        require(address(core2e[addr]) != address(0), "mocked map address is not set");
        return address(core2e[addr]).balance;
    }

    // function mappedNonce(address addr) external view returns (uint256);

    // interface for mock
    function setMockMapped(address coreAddress, bytes20 eAddress) public {
        core2e[coreAddress] = eAddress;
        // e2core[eAddress] = coreAddress;
    }

    // interface for mock
    function getMockMapped(address coreAddress) external view returns (bytes20) {
        require(core2e[coreAddress] != 0, "mock mapped address is not set");
        return core2e[coreAddress];
    }

    // function getMockReverseMapped(bytes20 eAddress) external view returns (address) {
    //     return e2core[eAddress];
    // }
}
