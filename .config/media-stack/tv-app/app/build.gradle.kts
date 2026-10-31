plugins {
    id("com.android.application")
}

android {
    namespace = "com.yesselman.watchtv"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.yesselman.watchtv"
        minSdk = 28
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
