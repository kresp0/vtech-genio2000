#ifndef GE_PROTO_H
#define GE_PROTO_H
/*
 * ge_proto.h - Genio -> PC protocol (transmit ONLY, DATA0 -> CP2102 RXD, 9600 8N1, T642 timing).
 *
 * Same framing as the hardware-validated firmware dump (SLIP + CRC-16/CCITT-FALSE, little-endian), with a different "magic":
 *   END(0xC0)  stuff( 'G' 'E' ver type seq16 len16 payload[len] crc16 )  END
 *   stuffing: 0xC0 -> DB DC, 0xDB -> DB DD.   crc16 = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) from 'G'..last byte of the payload,
 *   sent low byte first.  check("123456789") = 0x29B1.    seq16 = frame counter (starts at 0 on every start).
 * The DOCUMENT CONTENT and the DIAGNOSTIC EVENTS travel in different frame types (see examples/text-editor/docs/PROTOCOL.md).
 * The program that includes this file defines beforehand:  static void ge_tx_raw(byte b);
 */
#include "ge_types.h"

#define GE_SLIP_END 0xC0
#define GE_SLIP_ESC 0xDB
#define GE_SLIP_ESC_END 0xDC
#define GE_SLIP_ESC_ESC 0xDD
#define GE_PROTO_VER 1

#define GE_T_HELLO     0x01
#define GE_T_DOC_BEGIN 0x10
#define GE_T_DOC_DATA  0x11
#define GE_T_DOC_END   0x12
#define GE_T_KEY       0x20
#define GE_T_LED       0x22
#define GE_T_STATUS    0x30

#define GE_ST_DIAG_ENTER 1
#define GE_ST_DIAG_EXIT  2
#define GE_ST_EVQ_LOST   3
#define GE_ST_GHOST      4

static word pr_crc, pr_seq;

static void pr_stuffed(byte b) {
	if (b == GE_SLIP_END) { ge_tx_raw(GE_SLIP_ESC); ge_tx_raw(GE_SLIP_ESC_END); }
	else if (b == GE_SLIP_ESC) { ge_tx_raw(GE_SLIP_ESC); ge_tx_raw(GE_SLIP_ESC_ESC); }
	else ge_tx_raw(b);
}
/* Bit-by-bit CRC-16/CCITT-FALSE (no 512-byte table: the ROM is tight). Same function as the table of the dumper. */
static word pr_crc_step(word c, byte b) {
	byte i;
	c ^= (word)b << 8;
	for (i = 0; i < 8; i++) c = (word)((c & 0x8000) ? (c << 1) ^ 0x1021 : (c << 1));
	return c;
}
static void pr_crc_add(byte b) { pr_crc = pr_crc_step(pr_crc, b); }
static void pr_b(byte b) { pr_crc_add(b); pr_stuffed(b); }
static void pr_w(word w) { pr_b((byte)w); pr_b((byte)(w >> 8)); }
static void pr_begin(byte type, word len) {
	ge_tx_raw(GE_SLIP_END);
	pr_crc = 0xFFFF;
	pr_b('G'); pr_b('E'); pr_b(GE_PROTO_VER); pr_b(type); pr_w(pr_seq); pr_w(len);
	pr_seq++;
}
static void pr_end(void) {
	word c = pr_crc;
	pr_stuffed((byte)c); pr_stuffed((byte)(c >> 8));
	ge_tx_raw(GE_SLIP_END);
}

/* Incremental CRC-16 over a stream (for the CRC of the exported document) */
static word pr_stream_crc;
static void pr_stream_init(void) { pr_stream_crc = 0xFFFF; }
static void pr_stream_add(byte b) { pr_stream_crc = pr_crc_step(pr_stream_crc, b); }

#endif
