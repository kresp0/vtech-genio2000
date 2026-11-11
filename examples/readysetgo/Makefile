# READY, SET, GO! demo cartridge. Usage: make VGLDK=/path/to/vgldk   (needs sdcc, makebin, python3)
# VGLDK: a clone of https://github.com/hotkeymuc/vgldk at commit 6fbd389, unmodified.
VGLDK ?= ../../third_party/vgldk
NAME = readysetgo_gl2000
CART_SIZE_KB ?= 16
all: gen cart at28c256
gen: gen_demo.py gen_engine.py gen_music.py gen_scenes.py
	python3 gen_demo.py
cart:
	$(MAKE) -f $(abspath $(VGLDK))/tools/Makefile.mk cart NAME=$(NAME) VGLDK_SERIES=2000 CART_SIZE_KB=$(CART_SIZE_KB) \
		INC_DIR=$(abspath $(VGLDK))/include TOOLS_DIR=$(abspath $(VGLDK))/tools
# 32 KiB image for an AT28C256: the 16 KiB repeated (the CPU only sees the 0x8000-0xBFFF window)
at28c256:
	python3 -c "d=open('out/$(NAME).cart.$(CART_SIZE_KB)kb.bin','rb').read();open('$(NAME)_mirrored_AT28C256_32K.bin','wb').write(d*(32768//len(d)))"
clean:
	rm -rf out engine.h song.h scenes.h *.bin __pycache__ mame/__pycache__
.PHONY: all gen cart at28c256 clean
