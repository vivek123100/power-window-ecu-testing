"""Demo: a diagnostic session with the window ECU, frame by frame.

Scenario: the driver holds Up from 0.5 s to 2.5 s; the BCM goes silent from
1.0 to 2.0 s (lost message while moving -> DTC U0140-00).
The tester then reads the SW version, reads the DTCs, clears them, reads again.

Run from the repo root:   python3 03_CAN/sim/run_uds_demo.py
"""
import can_network as net
import sil_env
import uds

REQUESTS = [
    (3.0, bytes([0x22, 0xF1, 0x95]), "ReadDataByIdentifier: software version"),
    (3.5, bytes([0x19, 0x02, 0xFF]), "ReadDTCInformation: all stored DTCs"),
    (4.0, bytes([0x14, 0xFF, 0xFF, 0xFF]), "ClearDiagnosticInformation: all groups"),
    (4.5, bytes([0x19, 0x02, 0xFF]), "ReadDTCInformation again"),
    (5.0, bytes([0x22, 0x12, 0x34]), "ReadDataByIdentifier: unknown DID"),
]
KIND = {0: "SF", 1: "FF", 2: "CF", 3: "FC"}


def main():
    sil_env.build_library()
    lib = sil_env.load_library()
    tr = net.run_network(lib, stop_time=5.5, bcm_silent=(1.0, 2.0),
                         sw_up=((0, 0), (0.5, 1), (2.5, 0)),
                         diag_requests=[(t, r) for t, r, _ in REQUESTS])

    print("Diagnostic frames (0x7E0 tester -> ECU, 0x7E8 ECU -> tester):\n")
    for t, i, d in tr.frames:
        if i in (uds.REQ_ID, uds.RESP_ID):
            print(f"{t:5.2f}  {i:03X}  {KIND[d[0] >> 4]}  {d.hex(' ').upper()}")

    print("\nDecoded:")
    for (t_req, req, t_resp, resp), (_, _, text) in zip(tr.tester.log, REQUESTS):
        print(f"\n{text}\n  request : {req.hex(' ').upper()}\n  response: {resp.hex(' ').upper()}")
        if resp[0] == 0x62 and req[1:3] == bytes([0xF1, 0x95]):
            print(f"  -> software version '{resp[3:].decode()}'")
        elif resp[0] == 0x59:
            body = resp[3:]
            names = [uds.dtc_name(body[k:k + 3]) for k in range(0, len(body), 4)]
            print(f"  -> stored DTCs: {names or 'none'}")
        elif resp[0] == 0x7F:
            print(f"  -> negative response, NRC 0x{resp[2]:02X}")


if __name__ == "__main__":
    main()
