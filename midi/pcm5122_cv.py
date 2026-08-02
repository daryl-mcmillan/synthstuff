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


# set up 2ms pulse pins for clock and trigger
pulse_code = """
.program pulse_2ms
    pull block
    set pins, 1
    set x, 9 ; loop for a longer delay

count_loop:
    jmp x-- count_loop [19]  ; 20 cycle delay

    set pins, 0
"""
pulse_program = adafruit_pioasm.assemble(pulse_code)
def add_pulse_pin( pin ):
    return rp2pio.StateMachine(
        pulse_program,
        frequency=100_000,
        first_set_pin=pin,
        set_pin_count=1,
        initial_out_pin_state=0,
    )

def send_pulse(sm):
    array.array('i', [0])
    sm.write(array.array('i', [0]))

clock_pin = add_pulse_pin(board.GP2)
clock_24_pin = add_pulse_pin(board.GP3)
a_trigger_pin = add_pulse_pin(board.GP6)
b_trigger_pin = add_pulse_pin(board.GP7)

a_gate_pin = digitalio.DigitalInOut(board.GP8)
a_gate_pin.direction = digitalio.Direction.OUTPUT
b_gate_pin = digitalio.DigitalInOut(board.GP9)
b_gate_pin.direction = digitalio.Direction.OUTPUT

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
        send_pulse( clock_24_pin )
        if midi_clock % 24 == 0:
            # quarter note tick
            send_pulse( clock_pin )
        return
    current_midi_command = (current_midi_command << 8) + b[0]
    if ( current_midi_command & 0x00FF0000 ) == 0x00900000:
        set_note_cv( ( current_midi_command >> 8 ) & 0x7F )
        send_pulse( a_trigger_pin )
        a_gate_pin.value = True
        led.value = True
        current_midi_command = 0
        return
    if ( current_midi_command & 0x00FF0000 ) == 0x00800000:
        a_gate_pin.value = False
        led.value = False
        current_midi_command = 0
        return

while True:
    process_midi_command()

#    set_dc_val(2003238912)   # 2v
#    time.sleep(0.2)
#    set_dc_val(1001652224)   # 1v
#    time.sleep(0.2)
#    set_dc_val(0)  # 0v
#    time.sleep(0.2)
