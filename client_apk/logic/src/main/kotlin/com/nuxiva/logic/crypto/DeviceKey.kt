package com.nuxiva.logic.crypto

import org.bouncycastle.crypto.params.Ed25519PrivateKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import java.security.SecureRandom

public class DeviceKey private constructor(private val seed: ByteArray) {
    private val privateKey = Ed25519PrivateKeyParameters(seed, 0)
    private val publicBytes: ByteArray = privateKey.generatePublicKey().encoded

    public fun publicKey(): ByteArray = publicBytes.copyOf()

    public fun publicHex(): String = Hex.encode(publicBytes)

    public fun seedBytes(): ByteArray = seed.copyOf()

    public fun sign(message: ByteArray): ByteArray {
        val signer = Ed25519Signer()
        signer.init(true, privateKey)
        signer.update(message, 0, message.size)
        return signer.generateSignature()
    }

    public fun wipe() {
        seed.fill(0)
    }

    public companion object {
        public const val SEED_SIZE: Int = 32

        public fun generate(random: SecureRandom = SecureRandom()): DeviceKey {
            val seed = ByteArray(SEED_SIZE)
            random.nextBytes(seed)
            return DeviceKey(seed)
        }

        public fun fromSeed(seed: ByteArray): DeviceKey {
            require(seed.size == SEED_SIZE) { "device_key_invalid" }
            return DeviceKey(seed.copyOf())
        }
    }
}
