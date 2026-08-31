package com.shazamsync.app

data class ParsedShare(val title: String, val artists: List<String>)

/**
 * Shazam's share text looks like:
 *   "Thangame Thangame (From \"Idhayam Murali\") by S.S. Thaman, D Dheeraj & Vivek https://www.shazam.com/track/860590138/..."
 * i.e. "<title> by <artist(s)> <shazam.com track url>".
 */
object ShazamShareParser {
    // The title group is greedy so the split lands on the LAST " by ":
    // a title containing the word ("Killed by Death by Motörhead") would
    // otherwise be truncated at the first one.
    private val PATTERN = Regex("""^(.+) by (.+?) https?://\S+$""")

    fun parse(sharedText: String): ParsedShare? {
        val match = PATTERN.find(sharedText.trim()) ?: return null

        val title = match.groupValues[1].trim()
        val artistsRaw = match.groupValues[2].trim()
        if (title.isEmpty() || artistsRaw.isEmpty()) return null

        val artists = artistsRaw.split(",", "&")
            .map { it.trim() }
            .filter { it.isNotEmpty() }

        return ParsedShare(title, artists)
    }
}
