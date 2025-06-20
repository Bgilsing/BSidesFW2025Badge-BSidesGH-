from machine import Pin
import neopixel 
import time

from drivers.base import Driver

# Number of LEDs in the chain
NUM_LEDS = 7
FORWARD = 1
BACKWARD = -1

LED_COLOR = tuple

def scale_color(color: LED_COLOR, scale: float) -> LED_COLOR:
    """Scale the color values by the given scale factor."""
    return tuple(int(c * scale) for c in color)

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

class LEDs(Driver):
    def __init__(self):
        super().__init__()
        self.config.add('led_pin', 26)
        self.config.add('max_brightness_percent', 50)

        # Pin where WS2812 LEDs are connected
        led_pin = self.config['led_pin']
        if led_pin is None:
            raise ValueError("LED pin configuration is missing. Please set 'led_pin' in the config.")
        
        if not isinstance(led_pin, int):
            raise TypeError(f"LED pin must be an integer, got {type(led_pin).__name__} instead.")
        
        self.LEDpin = Pin(self.config['led_pin'])

        # Maximum brightness constant (0 to 1)
        max_brightness_percent = self.config['max_brightness_percent']
        if not (0 <= max_brightness_percent <= 100):
            raise ValueError(f"max_brightness_percent must be between 0 and 100, got {max_brightness_percent}.")
        # Convert percentage to a scale factor (0.0 to 1.0)
        self.max_brightness = max_brightness_percent / 100.0

        # SVH 2025-03-19 on V2 versions of the board, the LEDs have a very strange
        # timing bug that is causing LED artifacts. This is a workaround for that
        # bug. The timing values that MicroPython says are its defaults for 800 kHz
        # are (400, 850, 800, 450) for (T0H, T0L, T1H, T1L). 
        # 
        # 0 timing
        #   ┌───────┐        
        # <─| T0H   |    T0L
        #   |       └─────────────┘ 
        # 
        # 1 timing   
        #   ┌────────────┐        |
        # <─|   T1H      |   T1L  |
        #   |            └────────┘s
        # 
        # By changing the timings from the default to (400, 1500, 1500, 450) we are 
        # increasing the data significant time of the 0 bit and the 1 bit which makes it
        # more obvious/definitive to the LED what is a 0 and what is a 1.
        # 
        # The V3 board may have the same issue, but the trace distances are being adjusted
        # for the VX board that will hopefully resolve the issue, and the timings could be 
        # set back to the default.
        DEFAULT_TIMINGS = (400, 850, 800, 450)   # noqa: F841
        CUSTOM_TIMINGS = (400, 5000, 5000, 450)  # noqa: F841
        
        # Create a NeoPixel object
        self.leds = neopixel.NeoPixel(self.LEDpin, NUM_LEDS, timing=CUSTOM_TIMINGS)


    def set_led_color(self, led_index: int, color: LED_COLOR):
        """Turn on the LED at the given index with the specified color."""
        self.leds[led_index] = scale_color(color, self.max_brightness)
        self.leds.write()
    

    def turn_off_all(self):
        for led_num in range(NUM_LEDS):
            self.leds[led_num] = (0, 0, 0)
        
        self.leds.write()


    def turn_on_led(self, led_index):
        self.leds[led_index] = (0xFF, 0xFF, 0xFF)
        self.leds.write()


    def turn_off_led(self, led_index: int):
        """Turn off the LED at the given index."""
        self.set_led_color(led_index, (0, 0, 0))

    IN = 1
    OUT = -1
    FADE_DELAY_MS = 1
    def fade_led(self, led_index, color: LED_COLOR, in_or_out=1):
        """Fade in the LED at the given index with the specified color."""
        for i in range(0, 256):
            if in_or_out == self.IN:
                self.set_led_color(led_index, scale_color(color, i / 255))
            else:
                self.set_led_color(led_index, scale_color(color, 1 - i / 255))
            time.sleep_ms(self.FADE_DELAY_MS)


    def cross_fade(self, led1, led2, color1: LED_COLOR, color2: LED_COLOR):
        """Cross fade between two LEDs with the specified colors."""
        for i in range(0, 256):
            self.set_led_color(led1, scale_color(color1, 1 - i / 255))
            self.set_led_color(led2, scale_color(color2, i / 255))
            time.sleep_ms(self.FADE_DELAY_MS)


    def color_bounce(self, start_color, wait, fade=True, color_alternate=False):
        """Move up and down the LED strip with the specified color "Bounce" at 
        the ends of the strip. This is really more of a test routine but it 
        certainly could be used as an effect, or could at least be a selectable 
        fun routine in a list of routines

        Args:
            start_color (tuple): The color to use for the LEDs.
            wait (int): The delay in milliseconds between each LED.
            fade (bool): Whether to fade the LEDs in and out.
            color_alternate (bool): Whether to alternate the color levels on bouncing
        """
        direction = FORWARD
        index = 0
        while True:
            if fade:
                if index == 0 or index == NUM_LEDS - 1:
                    self.fade_led(index, start_color, self.IN)
                else:
                    self.cross_fade(index - direction, index, start_color, start_color)
            else:
                self.set_led_color(index, start_color)
                time.sleep_ms(wait)
                self.set_led_color(index, (0, 0, 0))
                

            index += direction
            if index == NUM_LEDS:
                direction = BACKWARD
                index = NUM_LEDS - 2
            elif index == -1:
                direction = FORWARD
                index = 1
                # swap all color levels
                if color_alternate:
                    save_color = start_color
                    start_color = (save_color[1], save_color[2], save_color[0])

    def rainbow_test_single_led(self, led_index, wait):
        """Perform the rainbow test on a specific LED."""
        for j in range(255):
            color = wheel(j & 255)
            self.leds[led_index] = scale_color(color, self.max_brightness)
            self.leds.write()
            time.sleep_ms(wait) # Delay in milliseconds
    
    def rainbow_test_all_leds(self, wait: int):
        for j in range(255):
            for led_num in range(NUM_LEDS):
                index_offset = (255 // NUM_LEDS) * led_num
                color = wheel((j + index_offset) & 255)
                self.leds[led_num] = scale_color(color, self.max_brightness)
                self.leds.write()
            
            time.sleep_ms(wait)

# while True:
#     # Perform the rainbow test on LED at index 3 (change the index as needed)
#     rainbow_test_single_led(1, 100)  # Adjust the speed by changing the delay (in milliseconds)