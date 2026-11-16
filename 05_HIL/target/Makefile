# Build the HIL firmware for the STM32F407: the ECU as a CAN node.
# Shares startup code and linker script with 04_PIL; controller from 02_SIL/src.
CC      = arm-none-eabi-gcc
SIZE    = arm-none-eabi-size
SRC_DIR = ../../02_SIL/src
PIL_DIR = ../../04_PIL/target
BUILD   = build

CFLAGS  = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 \
          -std=c99 -O2 -g -Wall -Wextra -Werror -ffunction-sections -fdata-sections \
          -I$(SRC_DIR)
LDFLAGS = -T $(PIL_DIR)/stm32f407.ld -nostartfiles --specs=nano.specs --specs=nosys.specs \
          -Wl,--gc-sections -Wl,-Map=$(BUILD)/hil_fw.map

SRCS = $(PIL_DIR)/startup.c main.c uds.c $(SRC_DIR)/window_ctrl.c $(SRC_DIR)/e2e_counter.c

$(BUILD)/hil_fw.elf: $(SRCS) uds.h $(PIL_DIR)/stm32f407.ld | $(BUILD)
	$(CC) $(CFLAGS) $(SRCS) $(LDFLAGS) -o $@
	$(SIZE) $@

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)

.PHONY: clean
