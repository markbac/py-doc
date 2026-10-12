#include <stdint.h>

int sensor_read(int16_t *temperature, uint16_t *humidity)
{
    /* Start a measurement, wait for it, then read both values over I2C. */
    if (i2c_start_measurement(SENSOR_ADDRESS) != 0) {
        return -1;
    }
    return i2c_read_values(SENSOR_ADDRESS, temperature, humidity);
}
