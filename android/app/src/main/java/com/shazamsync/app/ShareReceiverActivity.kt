package com.shazamsync.app

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

/** Placeholder baked into BuildConfig when a secrets.properties key is absent. */
private const val UNSET = "UNSET"

class ShareReceiverActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // A build made without app/secrets.properties compiles fine but points
        // nowhere; say so plainly instead of failing later as "couldn't find".
        if (BuildConfig.BACKEND_URL == UNSET || BuildConfig.BACKEND_API_KEY == UNSET ||
            BuildConfig.TARGET_PACKAGE_NAME == UNSET
        ) {
            toast("Shazam Sync isn't configured — see app/secrets.properties.example")
            finish()
            return
        }

        val sharedText = intent?.takeIf { it.action == Intent.ACTION_SEND && it.type == "text/plain" }
            ?.getStringExtra(Intent.EXTRA_TEXT)

        if (sharedText == null) {
            finish()
            return
        }

        val parsed = ShazamShareParser.parse(sharedText)
        if (parsed == null) {
            toast("Couldn't parse shared text")
            finish()
            return
        }

        BackendApi.search(parsed.title, parsed.artists) { result ->
            runOnUiThread {
                if (result == null) {
                    toast("Couldn't find '${parsed.title}' — not added")
                } else {
                    playTrack(result.videoId)
                    toast("Playing: ${parsed.title}")
                    BackendApi.addToPlaylist(result.videoId)
                }
                finish()
            }
        }
    }

    private fun playTrack(videoId: String) {
        val uri = Uri.parse("https://music.youtube.com/watch?v=$videoId")
        val playIntent = Intent(Intent.ACTION_VIEW, uri).apply {
            setPackage(BuildConfig.TARGET_PACKAGE_NAME)
        }
        // Package-visibility restrictions (API 30+) make resolveActivity()
        // unreliable for apps we haven't declared in a <queries> manifest
        // block, even when the target is genuinely installed and the intent
        // would succeed. Attempting the start directly and catching the
        // failure avoids that false negative.
        try {
            startActivity(playIntent)
        } catch (e: ActivityNotFoundException) {
            toast("Target app not installed: ${BuildConfig.TARGET_PACKAGE_NAME}")
        }
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
}
