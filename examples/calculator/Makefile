# Scientific calculator cartridge. Usage: make VGLDK=/path/to/vgldk   (needs sdcc, makebin, python3 with mpmath)
# VGLDK: a clone of https://github.com/hotkeymuc/vgldk at commit 6fbd389, unmodified.
VGLDK ?= ../../third_party/vgldk
NAME = calc_gl2000
all: gen cart image
gen: gen_tables.py gen_ui.py
	python3 gen_tables.py
cart:
	$(MAKE) -f $(abspath $(VGLDK))/tools/Makefile.mk cart CC="sdcc --opt-code-size" NAME=$(NAME) VGLDK_SERIES=2000 CART_SIZE_KB=16 \
		INC_DIR=$(abspath $(VGLDK))/include TOOLS_DIR=$(abspath $(VGLDK))/tools
image:
	python3 mkcart.py $(NAME)
tests/host: tests/host.c dec.h vm.h fmt.h eval.h consts.h tables.h tests/page2.h
	gcc -O1 -Wall -Wno-unused-function -o $@ tests/host.c
test: all
	tests/run_all.sh
clean:
	rm -rf out consts.h tables.h page2.bin tests/page2.h *_AT28C256_32K.bin *_mame_64K.bin __pycache__ tests/host
.PHONY: all gen cart image test clean
