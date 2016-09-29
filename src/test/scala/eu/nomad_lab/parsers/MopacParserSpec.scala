package eu.nomad_lab.parsers

import org.specs2.mutable.Specification

object MopacParserSpec extends Specification {
  "MopacParserTest" >> {
    "test with json-events" >> {
      ParserRun.parse(MopacParser, "parsers/mopac/test/examples/C6H6.out", "json-events") must_== ParseResult.ParseSuccess
    }
    "test with json" >> {
      ParserRun.parse(MopacParser, "parsers/mopac/test/examples/C6H6.out", "json") must_== ParseResult.ParseSuccess
    }
  }
}
