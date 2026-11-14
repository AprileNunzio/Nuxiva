package com.nuxiva.logic

import com.nuxiva.logic.enroll.EnrollmentParser
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ContractTest {
    private fun fixture(): JsonObject {
        var dir: File? = File("").absoluteFile
        while (dir != null && !File(dir, "contracts/android_enrollment.json").isFile) dir = dir.parentFile
        val file = requireNotNull(dir) { "contracts/android_enrollment.json not found" }.resolve("contracts/android_enrollment.json")
        return Json.parseToJsonElement(file.readText()).jsonObject
    }

    @Test
    fun theAppReadsEveryLinkTheServerGenerates() {
        val data = fixture()
        val now = data.getValue("now").jsonPrimitive.long
        val cases = data.getValue("cases") as JsonArray
        assertTrue(cases.isNotEmpty())
        cases.forEach { element ->
            val case = element.jsonObject
            val payload = case.getValue("payload").jsonObject
            val parsed = EnrollmentParser.parse(case.getValue("link").jsonPrimitive.content, now)
            val name = case.getValue("name").jsonPrimitive.content
            assertEquals(EnrollmentParser.normalizeServer(payload.getValue("server").jsonPrimitive.content), parsed.server, name)
            assertEquals(payload.getValue("token").jsonPrimitive.content, parsed.token, name)
            assertEquals(payload.getValue("pin").jsonPrimitive.content, parsed.pin, name)
            assertEquals(payload.getValue("expires").jsonPrimitive.long, parsed.expires, name)
        }
    }
}
