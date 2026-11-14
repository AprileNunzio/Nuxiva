package com.nuxiva.logic.crypto

public object Hex {
    private val digits = "0123456789abcdef".toCharArray()

    public fun encode(bytes: ByteArray): String {
        val out = CharArray(bytes.size * 2)
        for (index in bytes.indices) {
            val value = bytes[index].toInt() and 0xFF
            out[index * 2] = digits[value ushr 4]
            out[index * 2 + 1] = digits[value and 0x0F]
        }
        return String(out)
    }

    public fun decode(text: String): ByteArray {
        require(text.length % 2 == 0) { "hex_length" }
        val out = ByteArray(text.length / 2)
        for (index in out.indices) {
            val high = Character.digit(text[index * 2], 16)
            val low = Character.digit(text[index * 2 + 1], 16)
            require(high >= 0 && low >= 0) { "hex_digit" }
            out[index] = ((high shl 4) or low).toByte()
        }
        return out
    }
}
