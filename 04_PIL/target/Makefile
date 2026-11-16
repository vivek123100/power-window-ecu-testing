# Build the PIL firmware for the STM32F407 (Cortex-M4F with FPU).
# The controller sources come UNCHANGED from 02_SIL/src.
#   make            -> build/pil_fw.elf (+ size report)
#   make clean
CC      = arm-none-eabi-gcc
SIZE    = arm-none-eabi-size
SRC_DIR = ../../02_SIL/src
BUILD   = build

CFLAGS  = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 \
          -std=c99 -O2 -g -Wall -Wextra -Werror -ffunction-sections -fdata-sections \
          -I$(SRC_DIR)
LDFLAGS = -T stm32f407.ld -nostartfiles --specs=nano.specs --specs=nosys.specs \
          -Wl,--gc-sections -Wl,-Map=$(BUILD)/pil_fw.map

SRCS = startup.c main.c $(SRC_DIR)/window_ctrl.c $(SRC_DIR)/e2e_counter.c

$(BUILD)/pil_fw.elf: $(SRCS) stm32f407.ld | $(BUILD)
	$(CC) $(CFLAGS) $(SRCS) $(LDFLAGS) -o $@
	$(SIZE) $@

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)

.PHONY: clean
