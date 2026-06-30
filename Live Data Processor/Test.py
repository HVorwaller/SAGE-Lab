import board
import adafruit_hdc302x

i2c = board.I2C()

print("Testing0x44...")
sensor1 = adafruit_hdc302x.HDC302x(i2c, address=0x44)
print(sensor1.temperature)
print(sensor1.relative_humidity)

print("Testing0x45...")
sensor1 = adafruit_hdc302x.HDC302x(i2c, address=0x45)
print(sensor1.temperature)
print(sensor1.relative_humidity)