import board
import audiobusio
import audiocore
import array
import time

# 2v
raw_sample1 = audiocore.RawSample(array.array('h', [30567, 30567]), sample_rate=96000)

# 1v
raw_sample2 = audiocore.RawSample(array.array('h', [15284, 15284]), sample_rate=96000)

# 0v
raw_sample3 = audiocore.RawSample(array.array('h', [0, 0]), sample_rate=96000)

i2s = audiobusio.I2SOut(bit_clock=board.GP10, word_select=board.GP11, data=board.GP12)

while True:
    time.sleep(0.2)
    i2s.play(raw_sample1, loop=True)
    time.sleep(0.2)
    i2s.play(raw_sample2, loop=True)
    time.sleep(0.2)
    i2s.play(raw_sample3, loop=True)
