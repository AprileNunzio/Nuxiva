#include <stdio.h>
#include <string.h>

#include "edge_router.h"

int main() {
    static char line[4096];
    while (fgets(line, sizeof(line), stdin) != nullptr) {
        size_t length = strlen(line);
        while (length > 0 && (line[length - 1] == '\n' || line[length - 1] == '\r')) {
            line[--length] = '\0';
        }
        const nuxiva_edge::Decision d = nuxiva_edge::classify(line, length);
        printf("{\"intent\":\"%s\",\"confidence\":%.10f,\"agent\":\"%s\",\"action\":\"%s\",\"logits\":[%.6f,%.6f,%.6f,%.6f,%.6f],\"local\":%s}\n",
               nuxiva_edge::intent_name(d.intent), d.confidence, d.agent ? d.agent : "", d.action ? d.action : "",
               d.logits[0], d.logits[1], d.logits[2], d.logits[3], d.logits[4],
               nuxiva_edge::handle_locally(d, 0.85) ? "true" : "false");
    }
    return 0;
}
