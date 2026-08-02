import board
import busio
import digitalio
import rp2pio
import adafruit_pioasm
import array
import time

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# set up cv output via I2S

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

dc_memory_buffer = array.array('i', [0, 0])

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

sm.background_write(loop=dc_memory_buffer)

def set_note_cv(val):
    i = (val-64) * 83471018
    i = min( 0x7FFFFFFF, max( i, 0 - 0x80000000 ) )
    # this is the DMA buffer
    dc_memory_buffer[0] = i  # left
    dc_memory_buffer[1] = i  # right


# set up midi input
uart1 = busio.UART(
    tx=board.GP4,
    rx=board.GP5,
    baudrate=31250
)

current_midi_command = 0
midi_clock = 0

def process_midi_command():
    global current_midi_command
    global midi_clock

    b = uart1.read( 1 )
    if b is None or len(b) == 0:
        return
    if b[0] == 0xF8:
        midi_clock += 1
        # midi clock tick
        if midi_clock % 24 == 0:
            # quarter note tick
            pass
        return
    current_midi_command = (current_midi_command << 8) + b[0]
    if ( current_midi_command & 0x00FF0000 ) == 0x00900000:
        led.value = True
        set_note_cv( ( current_midi_command >> 8 ) & 0x7F )
        current_midi_command = 0
        return
    if ( current_midi_command & 0x00FF0000 ) == 0x00800000:
        led.value = False
        current_midi_command = 0
        return

while True:
    process_midi_command()
