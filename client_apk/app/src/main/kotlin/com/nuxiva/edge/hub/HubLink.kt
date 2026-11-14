package com.nuxiva.edge.hub

import com.nuxiva.edge.node.NodeFailure
import com.nuxiva.edge.node.NodeHttp
import com.nuxiva.edge.node.NodeProfile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive

object HubLink {
    private val path = Regex("/screen/open\\?t=[A-Za-z0-9_\\-]{16,128}")

    suspend fun open(profile: NodeProfile): String = withContext(Dispatchers.IO) {
        val reply = NodeHttp(profile).post("/api/nodes/display-link", JsonObject(emptyMap()))
        val relative = reply["path"]?.jsonPrimitive?.contentOrNull
        if (relative == null || !path.matches(relative)) throw NodeFailure.Server("invalid_response", 200)
        profile.server + relative
    }
}
