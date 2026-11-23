package com.nuxiva.logic.peer

public object PeerAddress {
    public const val MAX_HOST: Int = 253
    private val label = Regex("[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
    private val group = Regex("[0-9a-fA-F]{1,4}")

    public fun check(raw: String): Boolean {
        val cut = raw.lastIndexOf(':')
        if (cut < 0) return false
        val host = raw.substring(0, cut)
        val portText = raw.substring(cut + 1)
        if (portText.isEmpty() || portText.length > 5 || portText.any { it !in '0'..'9' }) return false
        val port = portText.toInt()
        if (port > 65535) return false
        val bracketed = host.length >= 2 && host.startsWith("[") && host.endsWith("]")
        val bare = if (bracketed) host.substring(1, host.length - 1) else host
        val v4 = ipv4(bare)
        val v6 = if (v4 == null) ipv6(bare) else null
        if (v4 != null) return !bracketed && port != 0 && acceptableV4(v4)
        if (v6 != null) return bracketed && port != 0 && acceptableV6(v6)
        if (looksNumeric(bare)) return false
        if (host.startsWith("[")) return false
        return port != 0 && host.isNotEmpty() && host.length <= MAX_HOST && host.split('.').all { label.matches(it) }
    }

    private fun looksNumeric(text: String): Boolean = text.isNotEmpty() && text.all { it in '0'..'9' || it == '.' }

    private fun acceptableV4(octets: IntArray): Boolean {
        if (octets.all { it == 0 }) return false
        if (octets[0] in 224..239) return false
        return !octets.all { it == 255 }
    }

    private fun acceptableV6(groups: IntArray): Boolean {
        if (groups.all { it == 0 }) return false
        return (groups[0] ushr 8) != 0xff
    }

    private fun ipv4(text: String): IntArray? {
        val parts = text.split('.')
        if (parts.size != 4) return null
        val out = IntArray(4)
        for (index in parts.indices) {
            val part = parts[index]
            if (part.isEmpty() || part.length > 3 || part.any { it !in '0'..'9' } || (part.length > 1 && part[0] == '0')) return null
            val value = part.toInt()
            if (value > 255) return null
            out[index] = value
        }
        return out
    }

    private fun ipv6(text: String): IntArray? {
        if (text.isEmpty() || text.any { it != ':' && it != '.' && Character.digit(it, 16) < 0 }) return null
        val doubled = text.indexOf("::")
        if (doubled >= 0 && text.indexOf("::", doubled + 1) >= 0) return null
        val head = if (doubled >= 0) text.substring(0, doubled) else text
        val tail = if (doubled >= 0) text.substring(doubled + 2) else ""
        val front = groups(head, allowV4 = doubled < 0) ?: return null
        val back = if (doubled >= 0) (groups(tail, allowV4 = true) ?: return null) else emptyList()
        val total = front.size + back.size
        if (doubled < 0) return if (total == 8) front.toIntArray() else null
        if (total > 7) return null
        return (front + List(8 - total) { 0 } + back).toIntArray()
    }

    private fun groups(text: String, allowV4: Boolean): List<Int>? {
        if (text.isEmpty()) return emptyList()
        val parts = text.split(':')
        val out = ArrayList<Int>(8)
        for (index in parts.indices) {
            val part = parts[index]
            if (index == parts.lastIndex && allowV4 && part.contains('.')) {
                val v4 = ipv4(part) ?: return null
                out += (v4[0] shl 8) or v4[1]
                out += (v4[2] shl 8) or v4[3]
            } else {
                if (!group.matches(part)) return null
                out += part.toInt(16)
            }
        }
        return out
    }
}
