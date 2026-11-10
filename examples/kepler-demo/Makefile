# Kepler demo cartridge. Usage: make VGLDK=/path/to/vgldk   (needs sdcc, makebin, python3)
# VGLDK: a clone of https://github.com/hotkeymuc/vgldk at commit 6fbd389 (see ../../docs/DEVELOPING.md).
VGLDK ?= ../../third_party/vgldk
NAME = kepler_demo_gl2000
CART_SIZE_KB ?= 16
all: gen cart at28c256
gen: gen_demo.py gen_helpers.py
	python3 gen_demo.py
cart:
	$(MAKE) -f $(VGLDK)/tools/Makefile.mk cart NAME=$(NAME) VGLDK_SERIES=2000 CART_SIZE_KB=$(CART_SIZE_KB) \
		INC_DIR=$(VGLDK)/include TOOLS_DIR=$(VGLDK)/tools
at28c256:
	python3 -c "d=open('out/$(NAME).cart.$(CART_SIZE_KB)kb.bin','rb').read();open('$(NAME)_mirrored_AT28C256_32K.bin','wb').write(d*(32768//len(d)))"
clean:
	rm -rf out song.h scenes.h loop.h helpers.h *.bin
.PHONY: all gen cart at28c256 clean
