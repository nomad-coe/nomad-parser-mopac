package eu.nomad_lab.parsers

import org.specs2.mutable.Specification

object MopacParserSpec extends Specification {
  "MopacParserTest" >> {
    "test with json-events" >> {
      ParserRun.parse(MopacParser, "parsers/mopac/test/examples/", "json-events") must_== ParseResult.ParseSuccess
    }
    "test with json" >> {
      ParserRun.parse(MopacParser, "parsers/mopac/test/examples/", "json") must_== ParseResult.ParseSuccess
    }
  }
}
