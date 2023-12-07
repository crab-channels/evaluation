from bitcoinutils.constants import SATOSHIS_PER_BITCOIN
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.script import Script
from identity import Id
from helper import print_tx, gen_secret
import math
# from typing import List


def main():
    """
    Run main to print the size of the different transactions to the console
    """
    # Some addresses on the testnet
    id_a = Id(
        '321ed233d302e10085ccbd51f035fdf7a83d76e3394cb4f0d0dde62301f97d8c')  # addr: mxtto7Jp5YSpxHX3S5axSytQ3QsJDaYWqz
    id_b = Id(
        '681b256f1517667f85ee87e0d82d3b0111009ab767ed07ea232ca452f8af5330')  # addr: mgiy2VgGHDH85xv8W1tGFttDwxCWrRe1nt
    id_channel = Id(
        '4d72721ba6f3b196fbd653171f861fa88dcdc330574c2e596ff0c84a5a1e7b7e')  # addr: mmAor5F2NXzdPfQYkBAbFCCsPMVVUgURAq
    id_revocation_a = Id(
        '5e7ca2ea95da55cd0c95b42113b374b8edce49845e052898720579bffbd5c811')  # addr: mpN83JK16JpWc9UzH6wJyNREXCCsE5GPXW
    id_revocation_b = Id(
        '4cca323073fab060dd1da6e5221811a1481ca72cdfbabff55e8b4304d1e0116b')  # addr: n49PdGf7LGtLuSk9e4SCDLsjCAj7mz4Z6Q

    tx_input_a = TxInput('e19be2f368063f6edc59710430f5a6037d939102d3ad4734651862c61c350915', 0)
    tx_input_b = TxInput('0f8c08c87ab006435e90b8a33bfd0546340568346c72fa0560e4bcfacd8808cd', 1)

    # SATOSHIS_PER_BITCOIN
    fee = 500
    eps = 1
    money_a = int(0.00008330 * SATOSHIS_PER_BITCOIN)
    money_b = int(0.00013996 * SATOSHIS_PER_BITCOIN)
    total = money_a + money_b
    c = 500
    v_a = math.floor((total - 2*c) * 0.4) # A hold 40%
    v_b = math.floor((total - 2*c) * 0.6) # B holds 60%
    delta = 2

    ft = get_ft(tx_input_a, tx_input_b, id_a, id_b, id_channel, v_a+v_b, c, fee)
    print_tx(ft, 'Funding tx')
    state_a = get_state(TxInput(ft.get_wtxid(), 0), id_channel, id_a, id_revocation_a, id_b, v_a, v_b, c, fee, delta)
    #         get_state(funding: TxInput, id_channel: Id, id_a: Id, id_revocation: Id, id_b: Id, v_a: int, v_b:float, c: int, fee: int, delta: int = 2)
    print_tx(state_a, 'State tx of A')
    pay_a = get_pay(TxInput(state_a.get_wtxid(), 0), TxInput(state_a.get_wtxid(), 1), id_a, id_b, id_revocation_a, c, v_a, fee, delta)
    #           get_pay(state: TxInput, id_a: Id, id_revocation: Id, c: int, v_a: int, fee: int, delta: int = 2) -> Transaction
    print_tx(pay_a, 'Pay tx of A')
    punish_a = get_punish(TxInput(state_a.get_wtxid(), 0), id_a, id_b, id_revocation_a, v_a, fee, delta)
    #          get_punish(state: TxInput, id_a: Id, id_revocation: Id, v_a: int, fee, delta: int = 2) -> Transaction:
    print_tx(punish_a, 'Punish tx of B on A')
    #####
    state_b = get_state(TxInput(ft.get_wtxid(), 0), id_channel, id_b, id_revocation_b, id_a, v_b, v_a, c, fee, delta)
    #         get_state(funding: TxInput, id_channel: Id, id_a: Id, id_revocation: Id, id_b: Id, v_a: int, v_b:float, c: int, fee: int, delta: int = 2)
    print_tx(state_b, 'State tx of B')
    pay_b = get_pay(TxInput(state_b.get_wtxid(), 0), TxInput(state_b.get_wtxid(), 1), id_b, id_a, id_revocation_b, c, v_b, fee, delta)
    #           get_pay(state: TxInput, id_a: Id, id_revocation: Id, c: int, v_a: int, fee: int, delta: int = 2) -> Transaction
    print_tx(pay_b, 'Pay tx of B')
    punish_b = get_punish(TxInput(state_b.get_wtxid(), 0), id_b, id_a, id_revocation_b, v_b, fee, delta)
    #          get_punish(state: TxInput, id_a: Id, id_revocation: Id, v_a: int, fee, delta: int = 2) -> Transaction:
    print_tx(punish_b, 'Punish tx of A on B')
    #####
    opt_close = get_close_opt(TxInput(ft.get_wtxid(), 0), id_channel, id_a, id_b, v_a, v_b, fee)
    print_tx(opt_close, 'Optimistic close')

def get_ft(input_a: TxInput, input_b: TxInput, id_a: Id, id_b: Id, id_channel: Id, f: int, c: int, fee: int) -> Transaction:
    # deduct 1 times fee, as this is a first level transaction
    tx_out0 = TxOutput(f + 2 * c - fee, id_channel.p2pkh)

    ft = Transaction([input_a, input_b], [tx_out0])

    sig_a = id_a.sk.sign_input(ft, 0, id_a.p2pkh)
    sig_b = id_b.sk.sign_input(ft, 1, id_b.p2pkh)

    input_a.script_sig = Script([sig_a, id_a.pk.to_hex()])
    input_b.script_sig = Script([sig_b, id_b.pk.to_hex()])

    return ft

def get_state(funding: TxInput, id_channel: Id, id_a: Id, id_revocation: Id, id_b: Id, v_a: int, v_b:float, c: int, fee: int, delta: int = 2) -> Transaction:
    # deduct 2 times fee, as this is a second level transaction, spending from f + 2 * c - fee
    outscript_a = Script(['OP_IF', 'OP_2', id_b.pk.to_hex(), id_revocation.pk.to_hex(), 'OP_CHECKMULTISIG', 'OP_CHECKSIG',
            'OP_ELSE', delta, 'OP_CHECKSEQUENCEVERIFY', 'OP_2', id_a.pk.to_hex(), id_b.pk.to_hex(), 'OP_2', 'OP_CHECKMULTISIG',
            'OP_ENDIF'])
    outscript_b = Script(['OP_IF', 'OP_DUP', 'OP_HASH160', id_revocation.pk.to_hash160(), 'OP_EQUALVERIFY', 'OP_CHECKSIG',
            'OP_ELSE', delta, 'OP_CHECKSEQUENCEVERIFY', 'OP_2', id_a.pk.to_hex(), id_b.pk.to_hex(), 'OP_2', 'OP_CHECKMULTISIG',
            'OP_ENDIF'])
    tx_out0 = TxOutput(v_a - fee, outscript_a)
    tx_out1 = TxOutput(c, outscript_b)
    tx_out2 = TxOutput(c + v_b - 2*fee - 260, id_b.p2pkh)

    state = Transaction([funding], [tx_out0, tx_out1, tx_out2])

    sig_ft = id_channel.sk.sign_input(state, 0, id_channel.p2pkh)

    funding.script_sig = Script([sig_ft, id_channel.pk.to_hex()])

    return state

def get_pay(state1: TxInput, state2: TxInput, id_a: Id, id_b: Id, id_revocation: Id, c: int, v_a: int, fee: int, delta: int = 2) -> Transaction:
    # deduct fee from output 1 of state holding c + v_a - fee
    tx_out = TxOutput(c + v_a - 2*fee, id_a.p2pkh)

    pay = Transaction([state1,state2], [tx_out])

    outscript_a = Script(['OP_IF', 'OP_2', id_b.pk.to_hex(), id_revocation.pk.to_hex(), 'OP_CHECKMULTISIG', 'OP_CHECKSIG',
            'OP_ELSE', delta, 'OP_CHECKSEQUENCEVERIFY', 'OP_2', id_a.pk.to_hex(), id_b.pk.to_hex(), 'OP_2', 'OP_CHECKMULTISIG',
            'OP_ENDIF'])
    outscript_b = Script(['OP_IF', 'OP_DUP', 'OP_HASH160', id_revocation.pk.to_hash160(), 'OP_EQUALVERIFY', 'OP_CHECKSIG',
            'OP_ELSE', delta, 'OP_CHECKSEQUENCEVERIFY', 'OP_2', id_a.pk.to_hex(), id_b.pk.to_hex(), 'OP_2', 'OP_CHECKMULTISIG',
            'OP_ENDIF'])

    sig_a = id_revocation.sk.sign_input(pay, 0, outscript_a)
    sig_b = id_revocation.sk.sign_input(pay, 0, outscript_b)

    state1.script_sig = Script(['OP_1', sig_a, sig_b, 'OP_0'])
    state2.script_sig = Script(['OP_1', sig_a, sig_b, 'OP_0'])

    return pay

def get_punish(state: TxInput, id_a: Id, id_b: Id, id_revocation: Id, v_a: int, fee, delta: int = 2) -> Transaction:
    # deduct fee from output 1 of state holding c + v_a - fee and give c to miners
    tx_out = TxOutput(v_a - 2*fee, id_b.p2pkh)

    punish = Transaction([state], [tx_out])

    outscript_a = Script(['OP_IF', 'OP_DUP', 'OP_HASH160', id_revocation.pk.to_hash160(), 'OP_EQUALVERIFY', 'OP_CHECKSIG',
            'OP_ELSE', delta, 'OP_CHECKSEQUENCEVERIFY', 'OP_DUP', 'OP_HASH160', id_a.pk.to_hash160(), 'OP_EQUALVERIFY', 'OP_CHECKSIG',
            'OP_ENDIF'])

    sig_r = id_revocation.sk.sign_input(punish, 0, outscript_a)

    state.script_sig = Script([sig_r, id_revocation.pk.to_hex(), 'OP_1'])

    return punish

def get_close_opt(funding: TxInput, id_channel: Id, id_a: Id, id_b: Id, v_a: int, v_b: int, fee) -> Transaction:
    # deduct 2 times fee, as this is a second level transaction, spending from ft holding v_a+v_b - fee
    tx_out0 = TxOutput(v_a - fee, id_a.p2pkh)
    tx_out1 = TxOutput(v_b - fee, id_b.p2pkh)

    close = Transaction([funding], [tx_out0, tx_out1])

    sig_channel = id_channel.sk.sign_input(close, 0, id_channel.p2pkh)

    funding.script_sig = Script([sig_channel, id_channel.pk.to_hex()])

    return close


if __name__ == "__main__":
    main()
