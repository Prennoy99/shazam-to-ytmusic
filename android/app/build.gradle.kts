import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val secretsFile = rootProject.file("app/secrets.properties")
val secrets = Properties().apply {
    if (secretsFile.exists()) {
        secretsFile.inputStream().use { load(it) }
    }
}

// Missing values fall back to an obvious placeholder rather than failing the
// build, so a fresh clone still syncs in Android Studio and builds in CI
// before anyone has written their own secrets.properties. The app detects
// the placeholder at runtime and tells you to configure it.
val UNSET = "UNSET"

fun secret(key: String): String {
    val value = secrets.getProperty(key)
    if (value.isNullOrBlank()) {
        logger.warn(
            "shazam-sync: '$key' is not set in app/secrets.properties — building with a " +
                "placeholder. Copy app/secrets.properties.example to app/secrets.properties " +
                "and fill it in before installing on a phone."
        )
        return UNSET
    }
    return value
}

android {
    namespace = "com.shazamsync.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.shazamsync.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        buildConfigField("String", "TARGET_PACKAGE_NAME", "\"${secret("targetPackageName")}\"")
        buildConfigField("String", "BACKEND_URL", "\"${secret("backendUrl")}\"")
        buildConfigField("String", "BACKEND_API_KEY", "\"${secret("backendApiKey")}\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    testImplementation("junit:junit:4.13.2")
}
