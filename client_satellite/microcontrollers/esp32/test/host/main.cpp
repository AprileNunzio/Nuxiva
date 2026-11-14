#include <stdio.h>

#include "check.h"

void run_identity_tests(const char* vectors_path);
void run_provision_tests();
void run_manifest_tests();
void run_action_tests();
void run_relay_tests();
void run_gate_tests();
void run_date_tests();

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: core_tests <esp32_vectors.json>\n");
        return 2;
    }
    run_identity_tests(argv[1]);
    run_provision_tests();
    run_manifest_tests();
    run_action_tests();
    run_relay_tests();
    run_gate_tests();
    run_date_tests();
    printf("%d checks, %d failed\n", check::total(), check::failures());
    return check::failures() == 0 ? 0 : 1;
}
