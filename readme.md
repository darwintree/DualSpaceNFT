## setup

```bash
pip install eth-brownie
brownie pm install OpenZeppelin/openzeppelin-contracts@4.9.0
```

## run test script

```bash

brownie console
```

then in brownie console

```
>>> run('setup-contracts')
```

## testnet deployment

There is currently testnet deployments. And here is a sample oracle configuration could be used for test.

- batch number: 20484047
- signer key: '0x4f29dd2ae711752ff3db97341b136926dc69bfc52f375c02b54d6d26cc2fe6f4'
- authorizer key: 0x3ebcced59d9709a245a385c17e0dd874a5d4f0162a6d9c6f14c3ca16819c6f88
