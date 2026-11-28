# GIANT.COM - splashscreen (NASM-versie)
# MSYS2 UCRT64:  pacman -S make mingw-w64-ucrt-x86_64-nasm \
#                         mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-pillow
all: GIANT.COM

logo.inc logo_data.inc: mklogo.py
	python mklogo.py preview.png

GIANT.COM: giant.asm logo.inc logo_data.inc
	nasm -f bin -o $@ giant.asm
	@ls -l $@

test: GIANT.COM
	python test_giant.py

clean:
	rm -f GIANT.COM preview.png test_*.png
