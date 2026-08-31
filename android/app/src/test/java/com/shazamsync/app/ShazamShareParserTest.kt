package com.shazamsync.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Shazam's share-text format is the one part of this pipeline we don't
 * control — an app update could change it at any time and would otherwise
 * break parsing silently. These lock in the shapes we've actually seen.
 */
class ShazamShareParserTest {

    @Test
    fun `parses a single artist`() {
        val parsed = ShazamShareParser.parse(
            "295 by Sidhu Moose Wala https://www.shazam.com/track/123456789/295"
        )
        assertEquals("295", parsed?.title)
        assertEquals(listOf("Sidhu Moose Wala"), parsed?.artists)
    }

    @Test
    fun `splits multiple artists on commas and ampersands`() {
        val parsed = ShazamShareParser.parse(
            "Thangame Thangame by S.S. Thaman, D Dheeraj & Vivek " +
                "https://www.shazam.com/track/860590138/thangame-thangame"
        )
        assertEquals("Thangame Thangame", parsed?.title)
        assertEquals(listOf("S.S. Thaman", "D Dheeraj", "Vivek"), parsed?.artists)
    }

    @Test
    fun `keeps parenthetical suffixes in the title`() {
        val parsed = ShazamShareParser.parse(
            "Thangame Thangame (From \"Idhayam Murali\") by S.S. Thaman " +
                "https://www.shazam.com/track/860590138/x"
        )
        assertEquals("Thangame Thangame (From \"Idhayam Murali\")", parsed?.title)
    }

    @Test
    fun `splits on the last 'by' so titles containing it survive`() {
        val parsed = ShazamShareParser.parse(
            "Stand By Me by Ben E. King https://www.shazam.com/track/1/stand-by-me"
        )
        assertEquals("Stand By Me", parsed?.title)
        assertEquals(listOf("Ben E. King"), parsed?.artists)

        val lowercase = ShazamShareParser.parse(
            "Killed by Death by Motörhead https://www.shazam.com/track/2/killed-by-death"
        )
        assertEquals("Killed by Death", lowercase?.title)
        assertEquals(listOf("Motörhead"), lowercase?.artists)
    }

    @Test
    fun `tolerates surrounding whitespace`() {
        val parsed = ShazamShareParser.parse(
            "  295 by Sidhu Moose Wala https://www.shazam.com/track/1/295  "
        )
        assertEquals("295", parsed?.title)
    }

    @Test
    fun `returns null for text that isn't a Shazam share`() {
        assertNull(ShazamShareParser.parse("just some copied text"))
        assertNull(ShazamShareParser.parse("https://www.shazam.com/track/1/295"))
        assertNull(ShazamShareParser.parse(""))
    }
}
