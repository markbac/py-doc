#include <stdint.h>

int read_meter(uint32_t *energy)
{
    /* Ask the meter, then wait for the answer. */
    return uart_request(METER_ENERGY, energy);
}
