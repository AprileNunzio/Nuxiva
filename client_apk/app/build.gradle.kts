plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

val signingPath = providers.environmentVariable("NUXIVA_KEYSTORE_PATH").orNull
val signingStorePassword = providers.environmentVariable("NUXIVA_KEYSTORE_PASSWORD").orNull
val signingAlias = providers.environmentVariable("NUXIVA_KEY_ALIAS").orNull
val signingKeyPassword = providers.environmentVariable("NUXIVA_KEY_PASSWORD").orNull
val signingReady = listOf(signingPath, signingStorePassword, signingAlias, signingKeyPassword).all { !it.isNullOrBlank() }

android {
    namespace = "com.nuxiva.edge"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.nuxiva.edge"
        minSdk = 26
        targetSdk = 34
        versionCode = 5008023
        versionName = "5.8.23"

        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86_64")
        }
    }

    signingConfigs {
        if (signingReady) {
            create("release") {
                storeFile = file(requireNotNull(signingPath))
                storePassword = signingStorePassword
                keyAlias = signingAlias
                keyPassword = signingKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (signingReady) signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources.excludes += setOf("/META-INF/{AL2.0,LGPL2.1}", "/META-INF/versions/**", "/META-INF/*.version")
    }

    lint {
        abortOnError = true
        checkReleaseBuilds = false
    }
}

dependencies {
    implementation(project(":logic"))
    implementation(platform("androidx.compose:compose-bom:2024.09.03"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("androidx.health.connect:connect-client:1.1.0-alpha10")
    implementation("androidx.camera:camera-core:1.3.4")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")
    implementation("com.google.guava:guava:33.3.1-android")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
