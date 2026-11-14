package com.nuxiva.logic.enroll

import com.nuxiva.logic.crypto.Hex
import java.security.SecureRandom

public object NodeIds {
    public val pattern: Regex = Regex("^[a-z0-9][a-z0-9-]{2,47}$")

    public fun generate(model: String, random: SecureRandom = SecureRandom()): String {
        val slug = model.lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-').take(30).trim('-').ifEmpty { "device" }
        val suffix = Hex.encode(ByteArray(3).also(random::nextBytes))
        return "android-$slug-$suffix"
    }
}
