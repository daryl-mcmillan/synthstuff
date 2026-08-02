import board
import rp2pio
import adafruit_pioasm
import array
import time

BCK_PIN = board.GP10   # Bit Clock
WSEL_PIN = board.GP11  # Word Select (LRCK)
DIN_PIN = board.GP12   # Data In

TARGET_SAMPLE_RATE = 96000
BITS_PER_SAMPLE = 32
PIO_CLOCK_FREQ = TARGET_SAMPLE_RATE * 2 * BITS_PER_SAMPLE * 2 # 2 cycles per bit

i2s_pio_asm = """
.program i2s_stereo
.side_set 2
.wrap_target

    ; --- Left Channel (WSEL = 0) ---
    set x, 30         side 0b01

left_loop:
    out pins, 1       side 0b00
    jmp x-- left_loop side 0b01

    out pins, 1      side 0b10
    set x, 30        side 0b11

    ; --- Right Channel (WSEL = 1) ---
right_loop:
    out pins, 1      side 0b10
    jmp x-- right_loop side 0b11

    out pins, 1      side 0b00
"""
compiled_asm = adafruit_pioasm.assemble(i2s_pio_asm)

dc_memory_buffer = array.array('i', [0, 0])  # Defaults to pure 0V ground out-of-box

sm = rp2pio.StateMachine(
    compiled_asm,
    frequency=PIO_CLOCK_FREQ,
    first_out_pin=DIN_PIN,
    out_pin_count=1,
    first_sideset_pin=BCK_PIN,
    sideset_pin_count=2,
    auto_pull=True,
    pull_threshold=32,
    out_shift_right=False        # MSB first
)

# set up DMA
sm.background_write(loop=dc_memory_buffer)

def set_dc_val(val):
    # this is the DMA buffer
    dc_memory_buffer[0] = val  # left
    dc_memory_buffer[1] = val  # right

while True:
    set_dc_val(2003238912)   # 2v
    time.sleep(0.2)
    set_dc_val(1001652224)   # 1v
    time.sleep(0.2)
    set_dc_val(0)  # 0v
    time.sleep(0.2)
