package com.nuxiva.logic.peer

import java.util.TreeMap

public data class MergeReport(val applied: Int, val known: Int, val rejected: Int)

internal class LedgerChain {
    private val blocks = ArrayDeque<LedgerBlock>()

    fun head(): LedgerBlock? = blocks.lastOrNull()

    fun all(): List<LedgerBlock> = blocks.toList()

    fun after(index: Long?): List<LedgerBlock> = blocks.filter { index == null || it.index > index }

    fun accept(block: LedgerBlock, now: Long): Boolean {
        if (block.ts > now + LedgerRules.SKEW_MILLIS) throw LedgerRules.fail("clock")
        val head = blocks.lastOrNull()
        if (head == null) {
            blocks.addLast(block)
            return true
        }
        if (block.index <= head.index) return settleOld(block)
        if (block.index != head.index + 1) throw LedgerRules.fail("gap")
        if (block.prev != LedgerRules.hash(head)) throw LedgerRules.fail("link")
        if (block.ts < head.ts) throw LedgerRules.fail("clock")
        blocks.addLast(block)
        while (blocks.size > LedgerRules.MAX_BLOCKS) blocks.removeFirst()
        return true
    }

    private fun settleOld(block: LedgerBlock): Boolean {
        val known = blocks.firstOrNull { it.index == block.index } ?: return false
        if (LedgerRules.hash(known) == LedgerRules.hash(block)) return false
        throw LedgerRules.fail("fork")
    }
}

public class Ledger(trusted: Collection<String> = emptyList()) {
    private val trust = linkedSetOf<String>()
    private val chains = TreeMap<String, LedgerChain>()
    private val failures = HashMap<Pair<String, String>, Int>()

    init {
        trusted.forEach { enroll(it) }
    }

    @Synchronized
    public fun enroll(node: String) {
        LedgerRules.checkId(node)
        if (node !in trust && trust.size >= LedgerRules.MAX_TRUSTED) throw LedgerRules.fail("capacity")
        trust.add(node)
    }

    @Synchronized
    public fun revoke(node: String): Boolean {
        chains.remove(node)
        failures.keys.removeAll { it.first == node }
        return trust.remove(node)
    }

    @Synchronized
    public fun accept(block: LedgerBlock, now: Long): Boolean {
        LedgerRules.checkShape(block)
        if (block.author !in trust) throw LedgerRules.fail("untrusted")
        if (block.author !in chains && chains.size >= LedgerRules.MAX_AUTHORS) throw LedgerRules.fail("capacity")
        LedgerRules.verify(block)
        val chain = chains.getOrPut(block.author) { LedgerChain() }
        val applied = try {
            chain.accept(block, now)
        } finally {
            if (chain.head() == null) chains.remove(block.author)
        }
        if (applied) failures.keys.removeAll { it.first == block.author }
        return applied
    }

    @Synchronized
    public fun latest(node: String): LedgerBlock? = chains[node]?.head()

    @Synchronized
    public fun candidates(node: String): List<String> {
        val head = latest(node) ?: return emptyList()
        return head.addrs.withIndex()
            .sortedWith(compareBy({ failures[node to it.value] ?: 0 }, { it.index }, { it.value }))
            .map { it.value }
    }

    @Synchronized
    public fun reportFailure(node: String, addr: String) {
        failures[node to addr] = (failures[node to addr] ?: 0) + 1
    }

    @Synchronized
    public fun reportSuccess(node: String, addr: String) {
        failures.remove(node to addr)
    }

    @Synchronized
    public fun digest(): List<LedgerHead> =
        chains.entries.mapNotNull { (author, chain) ->
            chain.head()?.let { LedgerHead(author, it.index, LedgerRules.hash(it)) }
        }

    @Synchronized
    public fun missingFor(remote: List<LedgerHead>): List<LedgerBlock> {
        val known = remote.associate { it.author to it.index }
        val found = ArrayList<LedgerBlock>()
        for ((author, chain) in chains) {
            found.addAll(chain.after(known[author]))
            if (found.size >= LedgerRules.MAX_SYNC) break
        }
        return found.take(LedgerRules.MAX_SYNC)
    }

    @Synchronized
    public fun merge(blocks: List<LedgerBlock>, now: Long): MergeReport {
        var applied = 0
        var known = 0
        var rejected = 0
        for (block in blocks.take(LedgerRules.MAX_SYNC).sortedWith(compareBy({ it.author }, { it.index }))) {
            try {
                if (accept(block, now)) applied += 1 else known += 1
            } catch (_: LedgerException) {
                rejected += 1
            }
        }
        return MergeReport(applied, known, rejected)
    }

    @Synchronized
    public fun answer(wire: LedgerWire): LedgerWire? = when (wire) {
        is LedgerWire.Want -> latest(wire.id)?.let { LedgerWire.Have(it) }
        is LedgerWire.Digest -> missingFor(wire.heads).takeIf { it.isNotEmpty() }?.let { LedgerWire.Delta(it) }
        is LedgerWire.Have, is LedgerWire.Delta -> null
    }

    @Synchronized
    public fun absorb(wire: LedgerWire, now: Long): MergeReport = when (wire) {
        is LedgerWire.Have -> merge(listOf(wire.block), now)
        is LedgerWire.Delta -> merge(wire.blocks, now)
        is LedgerWire.Want, is LedgerWire.Digest -> MergeReport(0, 0, 0)
    }

    public fun digestRequest(): LedgerWire = LedgerWire.Digest(digest())

    @Synchronized
    internal fun snapshot(): List<LedgerBlock> = chains.values.flatMap { it.all() }
}
