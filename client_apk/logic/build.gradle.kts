plugins {
    id("org.jetbrains.kotlin.jvm")
}

kotlin {
    jvmToolchain(17)
    explicitApi()
}

dependencies {
    implementation("org.bouncycastle:bcprov-jdk18on:1.78.1")
    api("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}
