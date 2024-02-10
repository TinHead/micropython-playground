from asyncio import run, create_task, sleep, sleep_ms, gather
from time import time
from rfm69 import RFM69
from machine import SPI, Pin
# from json import dumps

# init pins
CS = Pin(17, Pin.OUT, value=True)
RESET = Pin(21, Pin.OUT, value=False)
MISO = Pin(16)
MOSI = Pin(19)
SCK = Pin(18)
RELAY = Pin(22, Pin.OUT, value=True)
LED = Pin("LED", Pin.OUT, value=False)

MY_NAME = "centrala1001"
MY_ID = 1
MY_STATE = "OFF"
GW_UP = True


class gwState():
    def __init__(self):
        self.state = True
        self.ping_time = ""


class rfmMsg():
    def __init__(self, i, n, t, nt, p):
        self.id = i
        self.name = n
        self.msg_type = t
        self.node_type = nt
        self.payload = p

    def gen_msg(self, rssi):
        return bytes(self.id + ";" + self.name + ";"
                     + self.msg_type + ";" + self.node_type + ";"
                     + self.payload + ";" + str(rssi), "ascii")


def init_rfm69(cs, reset, sck, mosi, miso):
    spi = SPI(0, sck=sck, mosi=mosi, miso=miso)
    rfm = RFM69(spi=spi, nss=cs, reset=reset)
    rfm.frequency_mhz = 433.1
    rfm.node = MY_ID
    rfm.ack_retries = 5
    rfm.encryption_key = (
        b"\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08"
    )
    return rfm


async def present_me(rfm, msg):
    # send a presentation message every 60 seconds in case gw dies
    while True:
        print("Sending presentation to gw ..")
        rfm.destination = 0
        if rfm.send_with_ack(msg):
            print("Sent presentation!")
        else:
            print("Failed to send presentation!")
        await sleep(60)


async def recv_gw(rfm, state, ping, gw_state):
    while True:
        try:
            pkg = rfm.receive(with_ack=True)
        except RuntimeError as e:
            print("Got error", e, "Resetting RFM")
            rfm.reset()
            pkg = None
        if pkg is None:
            print("Nothing received ... moving on...")
        else:
            if pkg == "ON":
                print("Got ON message")
                state.payload = "ON"
                LED.high()
                RELAY.low()
                print("Sending state with ack", rfm.last_rssi)
                print(state.gen_msg(rfm.last_rssi))
                rfm.destination = 0
                if rfm.send_with_ack(state.gen_msg(rfm.last_rssi)):
                    print("Sent status!")
                else:
                    print("Failed to send status!")
            elif pkg == "OFF":
                print("Got OFF message")
                state.payload = "OFF"
                LED.low()
                RELAY.high()
                print("Sending state with ack", rfm.last_rssi)
                rfm.destination = 0
                if rfm.send_with_ack(state.gen_msg(rfm.last_rssi)):
                    print("Sent status!")
                else:
                    print("Failed to send status!")
            elif pkg == "ping":
                gw_state.state = True
                gw_state.ping_time = time()
                rfm.send(ping)
        await sleep_ms(1)


async def check_uptime(gw_state, node_state):
    while True:
        now = time()
        print(now, gw_state.ping_time)
        if now >= gw_state.ping_time+120:
            print("GW connection lost .. turning everything off")
            gw_state.state = False
            node_state.payload = "OFF"
            RELAY.high()
            LED.low()
        await sleep(60)


async def main():
    print("Starting up ...")
    print("Initialising RFM Radio ...")
    rfm = init_rfm69(CS, RESET, SCK, MOSI, MISO)
    print("RFM OK")
    present = rfmMsg(str(MY_ID), MY_NAME, "0", "switch", "OFF")
    state = rfmMsg(str(MY_ID), MY_NAME, "1", "switch", "OFF")
    ping = rfmMsg(str(MY_ID), MY_NAME, "2", "pong", "OFF")
    # start the async tasks
    gw_state = gwState()
    gw_state.ping_time = 0
    rssi = rfm.rssi
    recv_task = create_task(recv_gw(rfm, state, ping.gen_msg(rssi), gw_state))
    present_task = create_task(present_me(rfm, present.gen_msg(rssi)))
    uptime_task = create_task(check_uptime(gw_state, state))
    await gather(present_task, recv_task, uptime_task)

    while True:
        await sleep(0.5)
        LED.toggle()

run(main())
