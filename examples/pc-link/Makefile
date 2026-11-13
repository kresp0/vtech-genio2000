# PC -> Genio serial link test cartridge. Usage: make VGLDK=/path/to/vgldk   (needs sdcc, makebin, python3)
# VGLDK: a clone of https://github.com/hotkeymuc/vgldk at commit 6fbd389, unmodified.
VGLDK ?= ../../third_party/vgldk
NAME = pclink_gl2000
all: gen cart image
gen: gen_serial.py
	python3 gen_serial.py
cart:
	$(MAKE) -f $(abspath $(VGLDK))/tools/Makefile.mk cart NAME=$(NAME) VGLDK_SERIES=2000 CART_SIZE_KB=16 \
		INC_DIR=$(abspath $(VGLDK))/include TOOLS_DIR=$(abspath $(VGLDK))/tools
image:
	python3 mkcart.py $(NAME)
test: all
	tests/run_mame.sh
clean:
	rm -rf out serial.h *_16K.bin *_AT28C256_32K.bin __pycache__
.PHONY: all gen cart image test clean
