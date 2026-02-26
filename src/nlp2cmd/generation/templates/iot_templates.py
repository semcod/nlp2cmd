"""
IoT / Raspberry Pi domain templates for NLP2CMD.

Contains GPIO, sensors, device management, embedded Linux templates.
"""

IOT_TEMPLATES = {
    # Raspberry Pi — GPIO (raspi-gpio / pinctrl / python)
    'gpio_read': "raspi-gpio get {pin}",
    'gpio_set_high': "raspi-gpio set {pin} op dh",
    'gpio_set_low': "raspi-gpio set {pin} op dl",
    'gpio_set_input': "raspi-gpio set {pin} ip",
    'gpio_read_all': "raspi-gpio get",
    'pinctrl_get': "pinctrl get {pin}",
    'pinctrl_set': "pinctrl set {pin} {mode}",
    # Python GPIO
    'python_gpio_blink': "python3 -c \"import RPi.GPIO as GPIO; import time; GPIO.setmode(GPIO.BCM); GPIO.setup({pin}, GPIO.OUT); [GPIO.output({pin}, s) or time.sleep(0.5) for s in [True,False]*{count}]; GPIO.cleanup()\"",
    'python_gpio_read': "python3 -c \"import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup({pin}, GPIO.IN); print(GPIO.input({pin})); GPIO.cleanup()\"",
    # I2C
    'i2c_detect': "sudo i2cdetect -y {bus}",
    'i2c_get': "sudo i2cget -y {bus} {address} {register}",
    'i2c_set': "sudo i2cset -y {bus} {address} {register} {value}",
    'i2c_dump': "sudo i2cdump -y {bus} {address}",
    # SPI
    'spi_test': "sudo spidev_test -D /dev/spidev{bus}.{device}",
    # System info (RPi)
    'rpi_temp': "vcgencmd measure_temp",
    'rpi_voltage': "vcgencmd measure_volts",
    'rpi_clock': "vcgencmd measure_clock arm",
    'rpi_memory': "vcgencmd get_mem arm && vcgencmd get_mem gpu",
    'rpi_throttled': "vcgencmd get_throttled",
    'rpi_model': "cat /proc/device-tree/model",
    'rpi_config': "sudo raspi-config",
    'rpi_update': "sudo rpi-update",
    # Camera
    'camera_photo': "libcamera-still -o {output}",
    'camera_video': "libcamera-vid -t {duration} -o {output}",
    'camera_timelapse': "libcamera-still --timelapse {interval} -t {duration} -o {output_pattern}",
    'camera_stream': "libcamera-vid -t 0 --inline --listen -o tcp://0.0.0.0:{port}",
    # Sensors (python)
    'sensor_dht': "python3 -c \"import Adafruit_DHT; h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT{type}, {pin}); print(f'Temp: {{t:.1f}}°C, Humidity: {{h:.1f}}%')\"",
    'sensor_bme280': "python3 -c \"import bme280, smbus2; bus = smbus2.SMBus({bus}); data = bme280.sample(bus, {address}); print(f'{{data.temperature:.1f}}°C {{data.humidity:.1f}}% {{data.pressure:.1f}}hPa')\"",
    # Network / MQTT
    'mqtt_pub': "mosquitto_pub -h {host} -t '{topic}' -m '{message}'",
    'mqtt_sub': "mosquitto_sub -h {host} -t '{topic}'",
    'mqtt_pub_json': "mosquitto_pub -h {host} -t '{topic}' -m '{{\"sensor\": \"{sensor}\", \"value\": {value}}}'",
    # Device management
    'usb_list': "lsusb",
    'usb_details': "lsusb -v -d {vendor}:{product}",
    'serial_list': "ls /dev/tty*",
    'serial_connect': "minicom -D /dev/{device} -b {baudrate}",
    'serial_screen': "screen /dev/{device} {baudrate}",
    'bluetooth_scan': "sudo bluetoothctl scan on",
    'bluetooth_devices': "sudo bluetoothctl devices",
    'bluetooth_connect': "sudo bluetoothctl connect {mac}",
    # Home automation
    'homeassistant_api': "curl -s -H 'Authorization: Bearer {token}' {url}/api/states/{entity}",
    'homeassistant_service': "curl -s -X POST -H 'Authorization: Bearer {token}' -H 'Content-Type: application/json' -d '{{\"entity_id\": \"{entity}\"}}' {url}/api/services/{domain}/{service}",
    # System management
    'apt_install': "sudo apt-get install -y {package}",
    'apt_update': "sudo apt-get update && sudo apt-get upgrade -y",
    'firmware_update': "sudo rpi-eeprom-update -a",
    'hostname_set': "sudo hostnamectl set-hostname {hostname}",
    'wifi_scan': "sudo iwlist wlan0 scan | grep ESSID",
    'wifi_connect': "sudo nmcli device wifi connect '{ssid}' password '{password}'",
    'ip_address': "hostname -I",
}
