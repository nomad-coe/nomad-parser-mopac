package eu.nomad_lab.parsers

import org.specs2.mutable.Specification

object MopacParserSpec extends Specification {
  "CastepParserTest" >> {
    "test with json-events" >> {
      ParserRun.parse(CastepParser, "parsers/castep/test/examples/", "json-events") must_== ParseResult.ParseSuccess
    }
    "test with json" >> {
      ParserRun.parse(CastepParser, "parsers/castep/test/examples/", "json") must_== ParseResult.ParseSuccess
    }
  }
}
