package com.shazamsync.app

import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

data class SearchResult(val videoId: String, val matchedTitle: String?)

/**
 * Talks to the shazam-to-ytmusic backend. Search and playlist-add are
 * separate calls so the caller can fire the play intent as soon as search
 * resolves, without waiting on the playlist write.
 */
object BackendApi {
    // Render's free tier cold-starts a sleeping instance in ~30-50s; default
    // OkHttp timeouts (10s) would time out before that finishes and produce
    // a false "not found".
    private val client = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private fun request(path: String, body: JSONObject): Request =
        Request.Builder()
            .url("${BuildConfig.BACKEND_URL}$path")
            .addHeader("X-API-Key", BuildConfig.BACKEND_API_KEY)
            .post(body.toString().toRequestBody(JSON))
            .build()

    fun search(title: String, artists: List<String>, callback: (SearchResult?) -> Unit) {
        val body = JSONObject().apply {
            put("title", title)
            put("artists", JSONArray(artists))
        }
        client.newCall(request("/search", body)).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) = callback(null)

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (!it.isSuccessful) {
                        callback(null)
                        return
                    }
                    val json = JSONObject(it.body?.string() ?: "{}")
                    if (!json.optBoolean("found", false)) {
                        callback(null)
                        return
                    }
                    callback(SearchResult(json.getString("video_id"), json.optString("matched_title")))
                }
            }
        })
    }

    fun addToPlaylist(videoId: String) {
        val body = JSONObject().apply { put("video_id", videoId) }
        client.newCall(request("/add-to-playlist", body)).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) = Unit
            override fun onResponse(call: Call, response: Response) = response.close()
        })
    }
}
