# Text editor cartridge for the Spanish Genio 2000.
# Usage: make VGLDK=/path/to/vgldk   (a clone of https://github.com/hotkeymuc/vgldk at 6fbd389 with ../vgldk-genio applied; needs sdcc, makebin)
VGLDK ?= ../../third_party/vgldk
NAME = genio_text_editor_gl4000
all: image
cart:
	mkdir -p work && cp src/* work/
	cd work && $(MAKE) -f $(abspath $(VGLDK))/tools/Makefile.mk cart NAME=$(NAME) VGLDK_SERIES=4000 CART_SIZE_KB=32 \
		VGLDK_CFLAGS="-DGENIO_ES -DGENIO_NATIVE_CGROM" INC_DIR=$(abspath $(VGLDK))/include TOOLS_DIR=$(abspath $(VGLDK))/tools
# 32 KiB image for an AT28C256: the 16 KiB of code repeated twice (the CPU only sees the 0x8000-0xBFFF window)
image: cart
	python3 -c "d=open('work/out/$(NAME).cart.32kb.bin','rb').read()[:16384];open('$(NAME)_AT28C256_32K.bin','wb').write(d*2);print('code bytes: see the Used space line above (limit 16384)')"
clean:
	rm -rf work *_AT28C256_32K.bin
.PHONY: all cart image clean
